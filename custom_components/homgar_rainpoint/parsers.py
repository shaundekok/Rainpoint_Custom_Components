from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDevice:
    device_id: str
    device_name: str
    model: str
    model_code: int | None
    manufacturer: str = "RainPoint"
    sw_version: str | None = None
    via_device_id: str | None = None
    entities: list[dict[str, Any]] = field(default_factory=list)

    def add_entity(
        self,
        *,
        key: str,
        name: str,
        native_value: Any,
        device_class: str | None = None,
        state_class: str | None = None,
        native_unit_of_measurement: str | None = None,
        icon: str | None = None,
        entity_category: str | None = None,
        enabled_default: bool = True,
        suggested_display_precision: int | None = None,
        extra_state_attributes: dict[str, Any] | None = None,
    ) -> None:
        self.entities.append(
            {
                "unique_id": f"{self.device_id}_{key}",
                "key": key,
                "name": name,
                "native_value": native_value,
                "device_class": device_class,
                "state_class": state_class,
                "native_unit_of_measurement": native_unit_of_measurement,
                "icon": icon,
                "entity_category": entity_category,
                "enabled_default": enabled_default,
                "suggested_display_precision": suggested_display_precision,
                "extra_state_attributes": extra_state_attributes or {},
                "device_info": {
                    "identifiers": {("homgar_rainpoint", self.device_id)},
                    "name": self.device_name,
                    "manufacturer": self.manufacturer,
                    "model": self.model,
                    "sw_version": self.sw_version,
                },
            }
        )

    def build_entities(
        self, *, home: dict[str, Any], hub: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        for entity in self.entities:
            entity["home_name"] = home.get("homeName")
            entity["hub_name"] = hub.get("name")
        return {entity["unique_id"]: entity for entity in self.entities}


def _status_value(status_items: dict[str, dict[str, Any]], item_id: str) -> str | None:
    item = status_items.get(item_id)
    if item is None:
        return None
    return item.get("value")


def _battery_pct_from_12bit(hex_string: str) -> int | None:
    try:
        return round(int(hex_string, 16) / 4095 * 100)
    except Exception:
        return None


def _f_tenths_hex_to_c(part_a: str, part_b: str) -> float | None:
    if not part_a or not part_b:
        return None
    fahrenheit = int(part_a + part_b, 16) / 10
    return round((fahrenheit - 32) * 5 / 9, 2)


def _safe_slice(s: str, start: int, end: int) -> str:
    return s[start:end] if len(s) >= end else ""


def parse_hcs021frf(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Soil Moisture",
        model=subdevice.get("model", "HCS021FRF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        part1 = _safe_slice(payload, 29, 31)
        part2 = _safe_slice(payload, 27, 29)
        part3 = _safe_slice(payload, 25, 27)
        part4 = _safe_slice(payload, 21, 23)
        part5 = _safe_slice(payload, 17, 19)
        part6 = _safe_slice(payload, 15, 17)
        part7 = _safe_slice(payload, 33, 35)
        part8 = _safe_slice(payload, 31, 33)

        device.add_entity(
            key="temperature",
            name="Temperature",
            native_value=_f_tenths_hex_to_c(part5, part6),
            device_class="temperature",
            state_class="measurement",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="moisture",
            name="Moisture",
            native_value=int(part4, 16) if part4 else None,
            state_class="measurement",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="illuminance",
            name="Illuminance",
            native_value=round(int(part1 + part2 + part3, 16) / 10)
            if part1 and part2 and part3
            else None,
            device_class="illuminance",
            state_class="measurement",
            native_unit_of_measurement="lx",
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(part7 + part8)
            if part7 and part8
            else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_hcs012arf(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Rain Gauge",
        model=subdevice.get("model", "HCS012ARF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        p1 = _safe_slice(payload, 15, 17)
        p2 = _safe_slice(payload, 13, 15)
        p3 = _safe_slice(payload, 23, 25)
        p4 = _safe_slice(payload, 21, 23)
        p5 = _safe_slice(payload, 31, 33)
        p6 = _safe_slice(payload, 29, 31)
        p7 = _safe_slice(payload, 41, 43)
        p8 = _safe_slice(payload, 39, 41)
        p9 = _safe_slice(payload, 53, 55)
        p10 = _safe_slice(payload, 51, 53)

        device.add_entity(
            key="rain_1h",
            name="Rain 1 Hour",
            native_value=(int(p1 + p2, 16) / 10) if p1 and p2 else None,
            device_class="precipitation",
            state_class="measurement",
            native_unit_of_measurement="mm",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="rain_24h",
            name="Rain 24 Hours",
            native_value=(int(p3 + p4, 16) / 10) if p3 and p4 else None,
            device_class="precipitation",
            state_class="measurement",
            native_unit_of_measurement="mm",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="rain_7d",
            name="Rain 7 Days",
            native_value=(int(p5 + p6, 16) / 10) if p5 and p6 else None,
            device_class="precipitation",
            state_class="total_increasing",
            native_unit_of_measurement="mm",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="rain_total",
            name="Rain Total",
            native_value=(int(p7 + p8, 16) / 10) if p7 and p8 else None,
            device_class="precipitation",
            state_class="total_increasing",
            native_unit_of_measurement="mm",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=int(p9 + p10, 16) if p9 and p10 else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_hcs014arf(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Outdoor Sensor",
        model=subdevice.get("model", "HCS014ARF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        p1 = _safe_slice(payload, 7, 9)
        p2 = _safe_slice(payload, 5, 7)
        p3 = _safe_slice(payload, 11, 13)
        p4 = _safe_slice(payload, 9, 11)
        p5 = _safe_slice(payload, 25, 27)
        p6 = _safe_slice(payload, 23, 25)
        p7 = _safe_slice(payload, 29, 31)
        p8 = _safe_slice(payload, 35, 37)
        p9 = _safe_slice(payload, 33, 35)
        p10 = _safe_slice(payload, 39, 41)
        p11 = _safe_slice(payload, 37, 39)

        device.add_entity(
            key="temperature",
            name="Temperature",
            native_value=_f_tenths_hex_to_c(p5, p6),
            device_class="temperature",
            state_class="measurement",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_high",
            name="Temperature High",
            native_value=_f_tenths_hex_to_c(p3, p4),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_low",
            name="Temperature Low",
            native_value=_f_tenths_hex_to_c(p1, p2),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="humidity",
            name="Humidity",
            native_value=int(p7, 16) if p7 else None,
            device_class="humidity",
            state_class="measurement",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="humidity_high",
            name="Humidity High",
            native_value=int(p8, 16) if p8 else None,
            device_class="humidity",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="humidity_low",
            name="Humidity Low",
            native_value=int(p9, 16) if p9 else None,
            device_class="humidity",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(p10 + p11) if p10 and p11 else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_hcs008frf(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Flow Meter",
        model=subdevice.get("model", "HCS008FRF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        parts = {
            i: _safe_slice(payload, a, b)
            for i, (a, b) in enumerate(
                [
                    (49, 51),
                    (47, 49),
                    (45, 47),
                    (59, 61),
                    (57, 59),
                    (55, 57),
                    (69, 71),
                    (67, 69),
                    (65, 67),
                    (81, 83),
                    (79, 81),
                    (77, 79),
                    (91, 93),
                    (89, 91),
                    (87, 89),
                    (103, 105),
                    (101, 103),
                    (99, 101),
                    (97, 99),
                    (107, 109),
                    (109, 111),
                ],
                start=1,
            )
        }

        device.add_entity(
            key="current_used",
            name="Current Used",
            native_value=int(parts[1] + parts[2] + parts[3], 16) / 10
            if all(parts[i] for i in (1, 2, 3))
            else None,
            state_class="measurement",
            native_unit_of_measurement="L",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="current_duration",
            name="Current Duration",
            native_value=int(parts[4] + parts[5] + parts[6], 16)
            if all(parts[i] for i in (4, 5, 6))
            else None,
            native_unit_of_measurement="s",
        )
        device.add_entity(
            key="last_used",
            name="Last Used",
            native_value=int(parts[7] + parts[8] + parts[9], 16) / 10
            if all(parts[i] for i in (7, 8, 9))
            else None,
            state_class="measurement",
            native_unit_of_measurement="L",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="last_duration",
            name="Last Duration",
            native_value=int(parts[10] + parts[11] + parts[12], 16)
            if all(parts[i] for i in (10, 11, 12))
            else None,
            native_unit_of_measurement="s",
        )
        device.add_entity(
            key="total_today",
            name="Total Today",
            native_value=int(parts[13] + parts[14] + parts[15], 16) / 10
            if all(parts[i] for i in (13, 14, 15))
            else None,
            state_class="total_increasing",
            native_unit_of_measurement="L",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="total",
            name="Total",
            native_value=int(parts[16] + parts[17] + parts[18] + parts[19], 16) / 10
            if all(parts[i] for i in (16, 17, 18, 19))
            else None,
            state_class="total_increasing",
            native_unit_of_measurement="L",
            suggested_display_precision=1,
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(parts[20] + parts[21])
            if all(parts[i] for i in (20, 21))
            else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_HCS0528ARF(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "HCS0528ARF Sensor",
        model=subdevice.get("model", "HCS0528ARF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        p1 = _safe_slice(payload, 7, 9)
        p2 = _safe_slice(payload, 5, 7)
        p3 = _safe_slice(payload, 11, 13)
        p4 = _safe_slice(payload, 9, 11)
        p5 = _safe_slice(payload, 25, 27)
        p6 = _safe_slice(payload, 23, 25)
        p7 = _safe_slice(payload, 29, 31)
        p8 = _safe_slice(payload, 25, 27)

        device.add_entity(
            key="temperature",
            name="Temperature",
            native_value=_f_tenths_hex_to_c(p5, p6),
            device_class="temperature",
            state_class="measurement",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_high",
            name="Temperature High",
            native_value=_f_tenths_hex_to_c(p3, p4),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_low",
            name="Temperature Low",
            native_value=_f_tenths_hex_to_c(p1, p2),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(p7 + p8) if p7 and p8 else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_hcs0530tho(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Temperature / Humidity Sensor",
        model=subdevice.get("model", "HCS0530THO"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        p1 = _safe_slice(payload, 7, 9)
        p2 = _safe_slice(payload, 5, 7)
        p3 = _safe_slice(payload, 11, 13)
        p4 = _safe_slice(payload, 9, 11)
        p5 = _safe_slice(payload, 25, 27)
        p6 = _safe_slice(payload, 23, 25)
        p7 = _safe_slice(payload, 29, 31)
        p8 = _safe_slice(payload, 35, 37)
        p9 = _safe_slice(payload, 33, 35)
        p10 = _safe_slice(payload, 39, 41)
        p11 = _safe_slice(payload, 37, 39)
        p12 = _safe_slice(payload, 43, 45)

        device.add_entity(
            key="temperature",
            name="Temperature",
            native_value=_f_tenths_hex_to_c(p5, p6),
            device_class="temperature",
            state_class="measurement",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_high",
            name="Temperature High",
            native_value=_f_tenths_hex_to_c(p3, p4),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="temperature_low",
            name="Temperature Low",
            native_value=_f_tenths_hex_to_c(p1, p2),
            device_class="temperature",
            native_unit_of_measurement="°C",
            suggested_display_precision=2,
        )
        device.add_entity(
            key="humidity",
            name="Humidity",
            native_value=int(p7, 16) if p7 else None,
            device_class="humidity",
            state_class="measurement",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="humidity_high",
            name="Humidity High",
            native_value=int(p8, 16) if p8 else None,
            device_class="humidity",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="humidity_low",
            name="Humidity Low",
            native_value=int(p9, 16) if p9 else None,
            device_class="humidity",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(p10 + p11) if p10 and p11 else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="rssi",
            name="RF RSSI",
            native_value=(int(p12, 16) - 256) if p12 else None,
            device_class="signal_strength",
            state_class="measurement",
            native_unit_of_measurement="dBm",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_hcs026frf(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value
    device = ParsedDevice(
        device_id=str(subdevice["did"]),
        device_name=subdevice.get("name") or "Digital Soil Sensor",
        model=subdevice.get("model", "HCS026FRF"),
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )
    if payload:
        p1 = _safe_slice(payload, 15, 17)
        p2 = _safe_slice(payload, 19, 21)
        p3 = _safe_slice(payload, 17, 19)

        device.add_entity(
            key="moisture",
            name="Moisture",
            native_value=int(p1, 16) if p1 else None,
            state_class="measurement",
            native_unit_of_measurement="%",
        )
        device.add_entity(
            key="battery",
            name="Battery",
            native_value=_battery_pct_from_12bit(p2 + p3) if p2 and p3 else None,
            device_class="battery",
            state_class="measurement",
            native_unit_of_measurement="%",
            entity_category="diagnostic",
        )
        device.add_entity(
            key="debug",
            name="Debug Raw Value",
            native_value=payload,
            icon="mdi:code-json",
            entity_category="diagnostic",
            enabled_default=False,
        )
    return device


def parse_generic_raw(
    *, subdevice: dict[str, Any], status_items: dict[str, dict[str, Any]]
) -> ParsedDevice:
    """Fallback parser for unsupported RainPoint/Homgar subdevices."""
    model = subdevice.get("model") or "unknown_model"
    addr = subdevice.get("addr")
    did = str(subdevice.get("did") or f"unknown_{model}_{addr}")

    value = _status_value(status_items, f"D{subdevice['addr']:02d}") or ""
    payload = value.split(";", 1)[1] if ";" in value else value

    device = ParsedDevice(
        device_id=did,
        device_name=subdevice.get("name") or f"{model} Sensor",
        model=model,
        model_code=subdevice.get("modelCode"),
        via_device_id=str(subdevice.get("mid")) if subdevice.get("mid") is not None else None,
    )

    device.add_entity(
        key="raw_data",
        name="Raw Data",
        native_value=payload or value or None,
        icon="mdi:code-json",
        extra_state_attributes={
            "full_status_value": value or None,
            "model": model,
            "model_code": subdevice.get("modelCode"),
            "address": addr,
            "did": subdevice.get("did"),
            "mid": subdevice.get("mid"),
            "type": subdevice.get("type"),
        },
    )

    return device


SENSOR_PARSERS = {
    "HCS021FRF": parse_hcs021frf,
    "HCS012ARF": parse_hcs012arf,
    "HCS014ARF": parse_hcs014arf,
    "HCS008FRF": parse_hcs008frf,
    "HCS0528ARF": parse_HCS0528ARF,
    "HCS0530THO": parse_hcs0530tho,
    "HCS026FRF": parse_hcs026frf,
}