# Norsup Heat Pump - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for Norsup heat pumps using the **PC1004 controller** with AquaTemp WiFi module interface.

## Compatible devices

This integration works with pool heat pumps using the **Fairland PC1004** controller board, sold under various brand names:
- Norsup (e.g. P26TX/32)
  
## Requirements

- **RS485 to TCP/IP converter** connected to the heat pump's CN4 RS485 port
  - Tested with: USR-DR134
  - Settings: 9600 baud, 8N1, Modbus TCP → RTU (Simple Protocol Conversion)
- The AquaTemp WiFi module does **not** need to be connected

## How it works

This integration uses **passive RS485 bus sniffing** — it listens to the internal Modbus communication between the heat pump controller and its components, without interfering with normal operation.

Commands (setpoint, mode, silence, on/off) are sent via the AquaTemp WiFi module's slave address (0x63 / slave 99), which is how the original WiFi module communicates.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots → **Custom repositories**
4. Add: `https://github.com/yourusername/ha-norsup`
5. Category: **Integration**
6. Install **Norsup Pool Heat Pump**
7. Restart Home Assistant

### Manual

Copy `custom_components/norsup` to your `config/custom_components/` folder and restart.

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Norsup**
3. Enter the IP address of your RS485-to-TCP converter
4. Enter the port (default: 502)

## Entities

### Climate
| Entity | Description |
|--------|-------------|
| `climate.pool_heat_pump` | Main climate entity (setpoint + mode) |

### Sensors
| Entity | Description | Unit |
|--------|-------------|------|
| `sensor.inlet_water_temperature_t02` | Water inlet temp | °C |
| `sensor.outlet_water_temperature_t03` | Water outlet temp | °C |
| `sensor.ambient_temperature_t05` | Ambient temp | °C |
| `sensor.compressor_frequency_o07` | Compressor frequency | Hz |
| `sensor.compressor_load` | Compressor load | % |
| `sensor.compressor_current_o08` | Compressor current | A |
| `sensor.pressure_sensor_t10` | Refrigerant pressure | bar |
| ... | All T01-T19 and O06-O09 | |

### Switches
| Entity | Description |
|--------|-------------|
| `switch.pool_heat_pump_power` | On/Off |
| `switch.pool_heat_pump_silence_mode` | Silence mode |

## Wiring

```
Warmtepomp CN4          RS485 Hub          USR-DR134
──────────────          ─────────          ─────────
485A1 (A+) ─────────── A+ ──────────────── A
485B1 (B-) ─────────── B- ──────────────── B
GND ─────────────────── GND ─────────────── GND
12V ─────────────────── 12V (voor WiFi module optioneel)
```

## Technical details

### Modbus register map

**Read (passive sniffing) — FC16 slave 0, address 2001:**

| Index | Address | Code | Description | Unit | Scale |
|-------|---------|------|-------------|------|-------|
| 19 | 2020 | O06 | Expansion valve | N | x1 |
| 20 | 2021 | O07 | Compressor frequency | Hz | x1 |
| 21 | 2022 | O08 | Compressor current | A | x10 |
| 22 | 2023 | O09 | IPM temperature | °C | x10 |
| 44 | 2045 | T01 | Suction temperature | °C | x10 |
| 45 | 2046 | T02 | Inlet water temperature | °C | x10 |
| 46 | 2047 | T03 | Outlet water temperature | °C | x10 |
| 47 | 2048 | T04 | Coil temperature | °C | x10 |
| 48 | 2049 | T05 | Ambient temperature | °C | x10 |
| 49 | 2050 | T06 | Exhaust temperature | °C | x10 |
| 53 | 2054 | T10 | Pressure sensor | bar | x10 |
| 59 | 2060 | T11 | Superheat | °C | x10 |
| 60 | 2061 | T12 | Fan speed | rpm | x1 |
| 61 | 2062 | T13 | Overheat after compensation | °C | x10 |
| 62 | 2063 | T14 | Supply voltage | V | x1 |
| 64 | 2065 | T15 | Antifreeze temperature | °C | x10 |
| 66 | 2067 | T17 | Fan motor 1 speed | rpm | x1 |
| 67 | 2068 | T18 | Fan motor 2 speed | rpm | x1 |
| 68 | 2069 | T19 | Bus voltage | V | x1 |

**Write — FC16 slave 99 (AquaTemp WiFi module address 0x63):**

| Address | Function | Values |
|---------|----------|--------|
| 1011 | Power | 0=OFF, 1=ON |
| 1012 | Mode | 0=Cool, 1=Heat, 2=Auto |
| 1137 | Heating setpoint | °C × 10 (150-350) |
| 1013 | Cooling setpoint | °C × 10 (150-300) |
| 1076 | Silence mode | 0=OFF, 1=ON |

## Credits

Register map discovered through RS485 bus reverse engineering on a Norsup P26TX/32 with PC1004 controller.
