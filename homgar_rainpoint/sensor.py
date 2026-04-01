from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HomgarDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class HomgarSensorEntityDescription(SensorEntityDescription):
    enabled_default: bool = True


def _coerce_entity_category(value):
    if value is None:
        return None
    if isinstance(value, EntityCategory):
        return value
    if value == "diagnostic":
        return EntityCategory.DIAGNOSTIC
    if value == "config":
        return EntityCategory.CONFIG
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HomgarDataUpdateCoordinator = entry.runtime_data
    entities = [HomgarSensor(coordinator, entity) for entity in coordinator.data["entities"].values()]
    async_add_entities(entities)


class HomgarSensor(CoordinatorEntity[HomgarDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HomgarDataUpdateCoordinator, entity: dict) -> None:
        super().__init__(coordinator)
        self.entity_description = HomgarSensorEntityDescription(
            key=entity["key"],
            name=entity["name"],
            device_class=entity.get("device_class"),
            state_class=entity.get("state_class"),
            native_unit_of_measurement=entity.get("native_unit_of_measurement"),
            icon=entity.get("icon"),
            entity_category=_coerce_entity_category(entity.get("entity_category")),
            suggested_display_precision=entity.get("suggested_display_precision"),
        )
        self._attr_unique_id = entity["unique_id"]
        self._attr_entity_registry_enabled_default = entity.get("enabled_default", True)
        self._attr_device_info = DeviceInfo(**entity["device_info"])

    @property
    def native_value(self):
        return self.coordinator.data["entities"][self.unique_id]["native_value"]

    @property
    def extra_state_attributes(self):
        entity = self.coordinator.data["entities"][self.unique_id]
        attrs = dict(entity.get("extra_state_attributes", {}))
        attrs["home"] = entity.get("home_name")
        attrs["hub"] = entity.get("hub_name")
        return attrs