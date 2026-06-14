"""DataUpdateCoordinator for Norsup / Fairland Pool Heat Pump."""
from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    SLAVE_CMD,
    ADDR_POWER,
    ADDR_MODE,
    ADDR_SETPOINT_HEAT,
    ADDR_SETPOINT_COOL,
    ADDR_SILENCE,
    COMPRESSOR_MAX_HZ,
    SENSOR_REGISTERS,
)

_LOGGER = logging.getLogger(__name__)

MODBUS_TIMEOUT = 5
SETTINGS_TIMEOUT = 15


def s16(v: int) -> int:
    """Convert unsigned 16-bit to signed."""
    return v - 65536 if v > 32767 else v


def build_fc16(slave: int, start_addr: int, values: list[int]) -> bytes:
    """Build a Modbus FC16 write multiple registers packet."""
    count = len(values)
    byte_count = count * 2
    data = b"".join(struct.pack(">H", v) for v in values)
    length = 7 + byte_count
    return struct.pack(">HHHBB", 1, 0, length, slave, 16) + \
           struct.pack(">HHB", start_addr, count, byte_count) + data


def find_fc16_packets(buffer: bytes, slave: int, start_addr: int, min_regs: int) -> list[list[int]]:
    """Find FC16 write packets in buffer for given slave and start address."""
    results = []
    pos = 0
    while pos + 13 <= len(buffer):
        if (buffer[pos+2] == 0x00 and buffer[pos+3] == 0x00 and
                buffer[pos+6] == slave and buffer[pos+7] == 0x10):
            length = struct.unpack(">H", buffer[pos+4:pos+6])[0]
            total = 6 + length
            if total > 600 or pos + total > len(buffer):
                pos += 1
                continue
            if length > 5:
                sa = struct.unpack(">H", buffer[pos+8:pos+10])[0]
                rc = struct.unpack(">H", buffer[pos+10:pos+12])[0]
                bc = buffer[pos+12]
                if sa == start_addr:
                    regs = []
                    for i in range(min(rc, bc // 2)):
                        idx = pos + 13 + i * 2
                        if idx + 1 < len(buffer):
                            regs.append(struct.unpack(">H", buffer[idx:idx+2])[0])
                    if len(regs) >= min_regs:
                        results.append(regs)
            pos += total
        else:
            pos += 1
    return results


class NorsupCoordinator(DataUpdateCoordinator):
    """Coordinator for Norsup heat pump data."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.host = host
        self.port = port
        self._data: dict[str, Any] = {}

    def _connect(self) -> socket.socket:
        """Create a new TCP socket connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(MODBUS_TIMEOUT)
        sock.connect((self.host, self.port))
        return sock

    def _read_settings(self) -> dict[str, Any]:
        """
        Read power, mode, setpoints and silence via FC03 on slave 1.
        Hybrid: also picks up FC16 slave 99 packets if WiFi module is connected.
        """
        result: dict[str, Any] = {
            "power": None,
            "mode": None,
            "setpoint_cool": None,
            "setpoint_heat": None,
            "silence": None,
        }
        try:
            sock = self._connect()
            # Send FC03 requests
            req1 = struct.pack(">HHHBBHH", 0x0001, 0, 6, 1, 3, 1011, 3)  # power/mode/setpoint
            req2 = struct.pack(">HHHBBHH", 0x0002, 0, 6, 1, 3, 1137, 1)  # heat setpoint
            req3 = struct.pack(">HHHBBHH", 0x0003, 0, 6, 1, 3, 1076, 1)  # silence
            sock.send(req1)
            time.sleep(0.1)
            sock.send(req2)
            time.sleep(0.1)
            sock.send(req3)
            time.sleep(0.1)

            start = time.time()
            last_retry = start
            buffer = b""
            sock.settimeout(1)

            while time.time() - start < SETTINGS_TIMEOUT:
                # Retry req1 every 5s if power not received
                if result["power"] is None and time.time() - last_retry > 5:
                    sock.send(req1)
                    last_retry = time.time()

                try:
                    chunk = sock.recv(4096)
                    if chunk:
                        buffer += chunk
                        pos = 0
                        while pos + 8 <= len(buffer):
                            pid = struct.unpack(">H", buffer[pos+2:pos+4])[0]
                            if pid != 0:
                                pos += 1
                                continue
                            length = struct.unpack(">H", buffer[pos+4:pos+6])[0]
                            if length < 2 or length > 512:
                                pos += 1
                                continue
                            total = 6 + length
                            if pos + total > len(buffer):
                                break
                            slave = buffer[pos+6]
                            fc = buffer[pos+7]

                            # FC03 response slave 1, 3 regs (power/mode/setpoint_cool)
                            if (slave == 1 and fc == 3 and length == 9 and
                                    pos + 15 <= len(buffer) and result["power"] is None):
                                bc = buffer[pos+8]
                                if bc == 6:
                                    result["power"] = struct.unpack(">H", buffer[pos+9:pos+11])[0]
                                    result["mode"] = struct.unpack(">H", buffer[pos+11:pos+13])[0]
                                    result["setpoint_cool"] = struct.unpack(">H", buffer[pos+13:pos+15])[0]

                            # FC03 response slave 1, 1 reg (heat setpoint of silence)
                            elif (slave == 1 and fc == 3 and length == 5 and
                                    pos + 11 <= len(buffer)):
                                bc = buffer[pos+8]
                                if bc == 2:
                                    val = struct.unpack(">H", buffer[pos+9:pos+11])[0]
                                    if result["setpoint_heat"] is None:
                                        result["setpoint_heat"] = val
                                    elif result["silence"] is None:
                                        result["silence"] = val

                            # FC16 slave 99, adres 1001 (WiFi module aanwezig)
                            elif slave == 0x63 and fc == 0x10 and pos + 12 < len(buffer):
                                sa = struct.unpack(">H", buffer[pos+8:pos+10])[0]
                                bc = buffer[pos+12]
                                if sa == 1001 and bc >= 26:
                                    result["power"] = struct.unpack(">H", buffer[pos+13+20:pos+13+22])[0]
                                    result["mode"] = struct.unpack(">H", buffer[pos+13+22:pos+13+24])[0]
                                    result["setpoint_cool"] = struct.unpack(">H", buffer[pos+13+24:pos+13+26])[0]
                                elif sa == 1091 and bc >= 94:
                                    result["setpoint_heat"] = struct.unpack(">H", buffer[pos+13+92:pos+13+94])[0]

                            # FC16 slave 1, adres 1091 (verwarmingssetpoint backup)
                            elif slave == 0x01 and fc == 0x10 and pos + 12 < len(buffer):
                                sa = struct.unpack(">H", buffer[pos+8:pos+10])[0]
                                bc = buffer[pos+12]
                                if sa == 1091 and bc >= 94:
                                    result["setpoint_heat"] = struct.unpack(">H", buffer[pos+13+92:pos+13+94])[0]

                            pos += total
                        buffer = buffer[pos:]

                        if all(v is not None for v in result.values()):
                            break
                        if len(buffer) > 50000:
                            buffer = buffer[-10000:]
                except socket.timeout:
                    pass

            sock.close()
        except Exception as err:
            _LOGGER.warning("Error reading settings from %s: %s", self.host, err)

        return result

    def _read_sensors(self) -> list[int] | None:
        """Read sensor data via passive sniffing of FC16 slave 0 packets."""
        try:
            sock = self._connect()
            buffer = b""
            regs0 = None
            start = time.time()
            sock.settimeout(1)

            while time.time() - start < 10:
                try:
                    chunk = sock.recv(4096)
                    if chunk:
                        buffer += chunk
                        packets = find_fc16_packets(buffer, 0x00, 2001, 55)
                        if packets:
                            regs0 = packets[-1]
                            break
                        if len(buffer) > 50000:
                            buffer = buffer[-10000:]
                except socket.timeout:
                    pass

            sock.close()
            return regs0
        except Exception as err:
            _LOGGER.warning("Error reading sensors from %s: %s", self.host, err)
            return None

    def _write_register(self, addr: int, value: int) -> bool:
        """Write a single register to slave 99 via FC16."""
        try:
            sock = self._connect()
            req = build_fc16(SLAVE_CMD, addr, [value])
            sock.send(req)
            time.sleep(0.5)
            try:
                sock.settimeout(2)
                resp = sock.recv(256)
                if resp and len(resp) >= 8:
                    if resp[7] == 16:
                        sock.close()
                        return True
                    elif resp[7] & 0x80:
                        _LOGGER.error("Modbus exception %d writing addr %d", resp[8], addr)
            except socket.timeout:
                pass
            sock.close()
            return True  # Assume success if no exception response
        except Exception as err:
            _LOGGER.error("Error writing register %d: %s", addr, err)
            return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from heat pump."""
        try:
            # Run blocking I/O in executor
            settings = await self.hass.async_add_executor_job(self._read_settings)
            sensors = await self.hass.async_add_executor_job(self._read_sensors)

            data: dict[str, Any] = {}

            # Settings
            data["power"] = settings.get("power")
            data["mode"] = settings.get("mode")
            data["silence"] = settings.get("silence")

            # Setpoints
            sp_heat = settings.get("setpoint_heat")
            sp_cool = settings.get("setpoint_cool")
            if sp_heat is not None:
                data["setpoint_heat"] = s16(sp_heat) / 10
            if sp_cool is not None:
                raw = s16(sp_cool)
                data["setpoint_active"] = round(raw / 5) * 5 / 10

            # Compressor percentage
            if sensors and len(sensors) > 20:
                freq = s16(sensors[20])
                if freq > 0:
                    data["compressor_pct"] = min(100.0, freq / COMPRESSOR_MAX_HZ * 100)
                else:
                    data["compressor_pct"] = 0.0
                data["compressor_hz"] = max(0, freq)

            # Sensor registers
            if sensors:
                for code, reg in SENSOR_REGISTERS.items():
                    idx = reg["index"]
                    if idx < len(sensors):
                        raw = s16(sensors[idx])
                        scale = reg["scale"]
                        data[code] = raw / scale

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err

    # ── Write methods (called from entities) ─────────────────

    async def async_set_power(self, on: bool) -> None:
        """Turn heat pump on or off."""
        await self.hass.async_add_executor_job(
            self._write_register, ADDR_POWER, 1 if on else 0
        )
        await self.async_request_refresh()

    async def async_set_mode(self, mode: int) -> None:
        """Set operating mode (0=cool, 1=heat, 2=auto)."""
        await self.hass.async_add_executor_job(
            self._write_register, ADDR_MODE, mode
        )
        await self.async_request_refresh()

    async def async_set_setpoint_heat(self, temp: float) -> None:
        """Set heating setpoint."""
        value = int(temp * 10)
        await self.hass.async_add_executor_job(
            self._write_register, ADDR_SETPOINT_HEAT, value
        )
        await self.async_request_refresh()

    async def async_set_setpoint_cool(self, temp: float) -> None:
        """Set cooling setpoint."""
        value = int(temp * 10)
        await self.hass.async_add_executor_job(
            self._write_register, ADDR_SETPOINT_COOL, value
        )
        await self.async_request_refresh()

    async def async_set_silence(self, on: bool) -> None:
        """Enable or disable silence mode."""
        await self.hass.async_add_executor_job(
            self._write_register, ADDR_SILENCE, 1 if on else 0
        )
        await self.async_request_refresh()
