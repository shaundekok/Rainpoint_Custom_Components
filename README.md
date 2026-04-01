# Rainpoint API Custom Integration
Thank you to https://github.com/Remboooo for making this possible

Requirements:
1. Home Assistant
2. Rainpoint or Homgar Application:
   Logging in via this API will log you out in the app. It is advisable to create a separate API account from the app:
  - Log out from your main account
  - Create a new account
  - Log out and back into your main account
  - Invite your new account from 'Me' → 'Home management' → your home → 'Members'
  - Log out and back into your new account
  - Accept the invite
  - Make sure that you remove the default "home" that is created. Only the home with the sensors should remain in the 2nd accounts.
3. Rainpoint Device Address
   It is important that your sensor's device addresses are consecutive. Gaps in the numbering are casued when sensors are removed. I will look to implement a workaround in a future release.
  - Go through the list of sensors in the app from top to bottom.
  - Open each sensor, then click settings and review the device address.
  - The first sensor should be 1, then next 2, then 3 etc.
  - If they are not, remove the sensors that are after the gap and re-add them. This should close this gap and prevent the flow from erroring out.

Setup
1. Copy the homgar_rainpoint into the \config\custom_components\ folder in Home Assistant
2. Reboot your HA Instance
3. Add the Homgar/RainPoint Integration and provide the requested Details

Dashboard

<img width="1686" height="766" alt="dashboard" src="https://github.com/user-attachments/assets/afdc537f-5551-4b18-a319-7bd1d16d1762" />

Supported Devices:
1. RainPoint Smart+ Soil & Moisture Sensor (HCS021FRF) - New Decoder
2. RainPoint Smart+ High Precision Rain Sensor (HCS012ARF) - New Decoder
3. RainPoint Smart+ Water Flow Meter (HCS008FRF) - New Decoder
4. RainPoint Smart+ Air Quality Meter (HCS0530THO) | CO₂ Detector | Temp | Humidity - New Decoder
5. RainPoint Smart+ Temperature, Humidity & Lux Sensor (HCS014ARF) - New Decoder
6. RainPoint Smart+ Temperature & Humidity (HCS026FRF) - New Decoder
7. RainPoint Smart+ Smart Pool Thermometer (HCS0528ARF) - New Decoder
