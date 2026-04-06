# Homgar RainPoint custom integration

This custom integration talks directly to the Homgar cloud API used by RainPoint Smart+ devices.
It does **not** use MQTT.

## Included support from the Node-RED flow

- HCS021FRF soil moisture sensor
- HCS012ARF rain gauge
- HCS014ARF outdoor temperature/humidity sensor
- HCS008FRF flow meter
- Pool sensor model named `Pool`
- HCS0530THO CO2 sensor
- HCS026FRF digital soil moisture sensor

## Install

Copy `custom_components/homgar_rainpoint` into your Home Assistant `custom_components` directory and restart Home Assistant.
Then add the integration from **Settings → Devices & Services → Add Integration**.

## Notes

- Login is direct against the Homgar API, using the same MD5 password hashing pattern found in the Node-RED flow.
- The flow and the `homgarapi` project both indicate that API logins can invalidate or interfere with the mobile app session. Using a dedicated shared account is recommended.
- Unknown devices are skipped.
- Debug entities are created but disabled by default.