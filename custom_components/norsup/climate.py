"""Climate platform for Norsup / Fairland Pool Heat Pump."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SETPOINT_HEAT_MIN,
    SETPOINT_HEAT_MAX,
    SETPOINT_COOL_MIN,
    SETPOINT_COOL_MAX,
    MODE_NORSUP_TO_HA,
    MODE_HA_TO_NORSUP,
)
from .coordinator import NorsupCoordinator

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Norsup climate entity."""
    coordinator: NorsupCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, "Pool Heat Pump")
    async_add_entities([NorsupClimate(coordinator, entry, name)])


class NorsupClimate(CoordinatorEntity[NorsupCoordinator], ClimateEntity):
    """Climate entity for Norsup heat pump."""

    _attr_has_entity_name = True
    _attr_name = "Climate"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        coordinator: NorsupCoordinator,
        entry: ConfigEntry,
        device_name: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Norsup / Fairland",
            model="PC1004 Inverter Heat Pump",
        )

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        power = self.coordinator.data.get("power")
        if power == 0:
            return HVACMode.OFF
        mode = self.coordinator.data.get("mode")
        if mode is None:
            return HVACMode.OFF
        return MODE_NORSUP_TO_HA.get(mode, HVACMode.HEAT_COOL)

    @property
    def target_temperature(self) -> float | None:
        """Return current target temperature."""
        return self.coordinator.data.get("setpoint_heat")

    @property
    def current_temperature(self) -> float | None:
        """Return current water inlet temperature (T02)."""
        return self.coordinator.data.get("T02")

    @property
    def min_temp(self) -> float:
        """Return minimum temperature based on mode."""
        if self.hvac_mode == HVACMode.COOL:
            return SETPOINT_COOL_MIN
        return SETPOINT_HEAT_MIN

    @property
    def max_temp(self) -> float:
        """Return maximum temperature based on mode."""
        if self.hvac_mode == HVACMode.COOL:
            return SETPOINT_COOL_MAX
        return SETPOINT_HEAT_MAX

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_set_power(False)
        else:
            # Zet eerst aan als uitgezet
            if self.coordinator.data.get("power") == 0:
                await self.coordinator.async_set_power(True)
            norsup_mode = MODE_HA_TO_NORSUP.get(hvac_mode)
            if norsup_mode is not None:
                await self.coordinator.async_set_mode(norsup_mode)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature."""
        temp = kwargs.get("temperature")
        if temp is None:
            return
        if self.hvac_mode == HVACMode.COOL:
            await self.coordinator.async_set_setpoint_cool(temp)
        else:
            await self.coordinator.async_set_setpoint_heat(temp)
