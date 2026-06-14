"""Sensor platform for Norsup / Fairland Pool Heat Pump."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfFrequency,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_REGISTERS
from .coordinator import NorsupCoordinator

UNIT_MAP = {
    "°C":  UnitOfTemperature.CELSIUS,
    "A":   UnitOfElectricCurrent.AMPERE,
    "V":   UnitOfElectricPotential.VOLT,
    "bar": UnitOfPressure.BAR,
    "Hz":  UnitOfFrequency.HERTZ,
    "rpm": "rpm",
    "":    None,
}

DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "current":     SensorDeviceClass.CURRENT,
    "voltage":     SensorDeviceClass.VOLTAGE,
    "pressure":    SensorDeviceClass.PRESSURE,
}

EXTRA_SENSORS = [
    {"key": "compressor_pct", "name": "Compressor Load",    "unit": "%",   "device_class": None, "icon": "mdi:gauge"},
    {"key": "compressor_hz",  "name": "Compressor Frequency (raw)", "unit": "Hz", "device_class": None, "icon": "mdi:sine-wave"},
    {"key": "setpoint_heat",  "name": "Heating Setpoint",   "unit": "°C",  "device_class": "temperature", "icon": "mdi:thermometer-plus"},
    {"key": "setpoint_active","name": "Active Setpoint",    "unit": "°C",  "device_class": "temperature", "icon": "mdi:thermometer"},
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Norsup sensors."""
    coordinator: NorsupCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, "Pool Heat Pump")

    entities = []

    # T and O parameter sensors
    for code, reg in SENSOR_REGISTERS.items():
        entities.append(
            NorsupSensor(
                coordinator=coordinator,
                entry=entry,
                device_name=name,
                data_key=code,
                sensor_name=f"{reg['name']} ({code})",
                unit=UNIT_MAP.get(reg["unit"]),
                device_class=DEVICE_CLASS_MAP.get(reg["device_class"]),
                icon=_icon_for_unit(reg["unit"]),
            )
        )

    # Extra sensors
    for s in EXTRA_SENSORS:
        entities.append(
            NorsupSensor(
                coordinator=coordinator,
                entry=entry,
                device_name=name,
                data_key=s["key"],
                sensor_name=s["name"],
                unit=UNIT_MAP.get(s["unit"], s["unit"]),
                device_class=DEVICE_CLASS_MAP.get(s["device_class"]),
                icon=s.get("icon"),
            )
        )

    async_add_entities(entities)


def _icon_for_unit(unit: str) -> str:
    return {
        "°C":  "mdi:thermometer",
        "A":   "mdi:current-ac",
        "V":   "mdi:lightning-bolt",
        "bar": "mdi:gauge",
        "Hz":  "mdi:sine-wave",
        "rpm": "mdi:fan",
        "":    "mdi:information",
    }.get(unit, "mdi:information")


class NorsupSensor(CoordinatorEntity[NorsupCoordinator], SensorEntity):
    """Representation of a Norsup sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NorsupCoordinator,
        entry: ConfigEntry,
        device_name: str,
        data_key: str,
        sensor_name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        icon: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_name = sensor_name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{data_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Norsup / Fairland",
            model="PC1004 Inverter Heat Pump",
        )

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self.coordinator.data.get(self._data_key)
