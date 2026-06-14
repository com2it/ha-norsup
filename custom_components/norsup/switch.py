"""Switch platform for Norsup / Fairland Pool Heat Pump."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NorsupCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Norsup switches."""
    coordinator: NorsupCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, "Pool Heat Pump")
    async_add_entities([
        NorsupPowerSwitch(coordinator, entry, name),
        NorsupSilenceSwitch(coordinator, entry, name),
    ])


class NorsupBaseSwitch(CoordinatorEntity[NorsupCoordinator], SwitchEntity):
    """Base switch for Norsup."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NorsupCoordinator,
        entry: ConfigEntry,
        device_name: str,
        key: str,
        switch_name: str,
        icon_on: str,
        icon_off: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._key = key
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._attr_name = switch_name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Norsup / Fairland",
            model="PC1004 Inverter Heat Pump",
        )

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        return self._icon_on if self.is_on else self._icon_off


class NorsupPowerSwitch(NorsupBaseSwitch):
    """Switch to turn heat pump on/off."""

    def __init__(self, coordinator, entry, device_name):
        super().__init__(
            coordinator, entry, device_name,
            key="power",
            switch_name="Power",
            icon_on="mdi:power",
            icon_off="mdi:power-off",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if heat pump is on."""
        power = self.coordinator.data.get("power")
        if power is None:
            return None
        return power == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the heat pump on."""
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the heat pump off."""
        await self.coordinator.async_set_power(False)


class NorsupSilenceSwitch(NorsupBaseSwitch):
    """Switch to enable/disable silence mode."""

    def __init__(self, coordinator, entry, device_name):
        super().__init__(
            coordinator, entry, device_name,
            key="silence",
            switch_name="Silence Mode",
            icon_on="mdi:volume-off",
            icon_off="mdi:volume-high",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if silence mode is on."""
        silence = self.coordinator.data.get("silence")
        if silence is None:
            return None
        return silence == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Enable silence mode."""
        await self.coordinator.async_set_silence(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable silence mode."""
        await self.coordinator.async_set_silence(False)
