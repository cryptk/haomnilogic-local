# Hayward OmniLogic Local API integration for HomeAssistant

A Home Assistant integration for Hayward OmniLogic/OmniHub pool controllers using the local UDP/XML api

## Installation
This repository is able to be installed via [HACS](https://hacs.xyz/), you will need to add this repo as a [Custom Repository](https://hacs.xyz/docs/faq/custom_repositories/)

## Configuration
Your OmniLogic/OmmniHub needs to have a static IP address configured, please consult the documentation for your network router for how to accomplish this.

The only parameter you should need to configure is the IP address.

## Functionality
This addon is not complete, initially I am implementing all functionality for the equipment that I have.  If you have equipmment or functionality that is not supported in the addon, please don't hesitate to [Open an Issue](https://github.com/cryptk/haomnilogic-local/issues)

- Multiple bodies of water represented as separate devices
- Pumps/Filter Pumps
    - Turn on/off
    - Set speed to high/med/low presets
    - Set speed to custom value
- Lights
    - Turn on/off
    - Set brightness
    - Set show/effect
- Relays (Valve Actuators/High Voltage)
    - Turn on/off
- Sensors
    - Temperature
    - Service Mode
- Heaters
    - Turn on/off
    - View current temperature
    - Adjust set temperature

## Known Limitations
Aside from not yet supporting all hardware that exists within the OmniLogic, there is currently a limitation of one installation of the integration.  This means one omnilogic per Home Assistant install.  I may be able to lift this limitation later, but it's low on the priority list.

While I will eventually support turning schedules on/off and triggering themes, I have no current plans to add support for creating/deleting schedules/themes within the integration. If this functionality was added, it would need a custom service to do so, and I don't think the use case is there.  If you would like to see this functionality, plase [open an issue](https://github.com/cryptk/haomnilogic-local/issues)

## Credits

The work on this integration would not have been possible without the efforts of [djtimca](https://github.com/djtimca/) and [John Sutherland](garionphx@gmail.com)