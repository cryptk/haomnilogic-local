# Hayward OmniLogic Local API integration for HomeAssistant

A Home Assistant integration for Hayward OmniLogic/OmniHub pool controllers using the local UDP/XML api

[![Buy me a coffee!](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cryptk)

## Installation
This repository is able to be installed via [HACS](https://hacs.xyz/), you will need to add this repo as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/)

## Configuration
Your OmniLogic/OmniHub needs to have a static IP address configured, please consult the documentation for your network router for how to accomplish this.

The only parameter you should need to configure is the IP address.

The Scan Interval setting controls how often the controller is polled.  Per home-assistant recommendations/requirements, the minimum value is 5.

## Functionality
This addon is not complete, initially I am implementing all functionality for the equipment that I have.  If you have equipmment or functionality that is not supported in the addon, please don't hesitate to [Open an Issue](https://github.com/cryptk/haomnilogic-local/issues)

- Multiple bodies of water represented as separate devices
- Pumps/Filter Pumps
    - Variable speed and single speed
    - Turn on/off
    - Set speed to high/med/low presets (if variable speed)
    - Set speed to custom value (if variable speed)
- Lights
    - Turn on/off
    - Set brightness
    - Set show/effect
- Relays (Valve Actuators/High Voltage)
    - Turn on/off
- Sensors
    - Flow
    - Filter pump power (not usable in the energy dashboard directly, [see below](#why-cant-i-add-the-pump-power-sensors-to-the-energy-dashboard))
    - Temperature
    - Service Mode
- Heaters
    - Turn on/off
    - View current temperature
    - Adjust set temperature
- Chlorinators
    - Timed Percent control (no ORP control yet)
    - Enable/Disable
    - Adjust timed percent target
- Schedules
    - Restore Idle button to revert pool to configured schedule

## Known Limitations
Aside from not yet supporting all hardware that exists within the OmniLogic, there is currently a limitation of one installation of the integration.  This means one omnilogic per Home Assistant install.  I may be able to lift this limitation later, but it's low on the priority list.

While I will eventually support turning schedules on/off and triggering themes, I have no current plans to add support for creating/deleting schedules/themes within the integration. If this functionality was added, it would need a custom service to do so, and I don't think the use case is there.  If you would like to see this functionality, please [open an issue](https://github.com/cryptk/haomnilogic-local/issues)

Dual speed pumps/filters are not currently supported, only single speed and variable speed.  If you have a dual speed pump/filter that we can test with, please [open an issue](https://github.com/cryptk/haomnilogic-local/issues).

Chlorinators with ORP control are not supported yet.  If you have a chlorinator using ORP control that we can test with, please [open an issue](https://github.com/cryptk/haomnilogic-local/issues).

## Common questions/issues
### Why can't I add the pump power sensors to the Energy dashboard
The Omni reports Power (instantaneous usage, watts) whereas the dashboard consumes Energy sensors (usage over time, watt-hours). Luckily, we can use a Home Assistant helper to convert the data.

1. Under Settings > Devices & Services > Helpers, select Create Helper
1. Select "Integration- Riemann sum integral sensor"
1. Fill out the integration with the following settings
    - Name: You can select this, make it descriptive
    - Input Sensor: select your power sensor
    - Integration method: Left Riemann sum
    - Precision: 2
    - Metric prefix: none
    - Time unit: Hours
1. Add this new sensor to your Energy Dashboard
1. It will take 1-2 hours for statistics to generate, this is an hourly scheduled task in Home Assistant.


## Credits

The work on this integration would not have been possible without the efforts of [djtimca](https://github.com/djtimca/) and [John Sutherland](garionphx@gmail.com) on the initial API library code as well as Paulbhyo and MHillyer on the testing of initial versions of the integration.
