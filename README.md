# Hayward OmniLogic Local API integration for HomeAssistant

A Home Assistant integration for Hayward OmniLogic/OmniHub pool controllers using the local UDP/XML api

## Installation
This repository is able to be installed via [HACS](https://hacs.xyz/)

## Configuration
Your OmniLogic/OmmniHub needs to have a static IP address configured, please consult the documentation for your network router for how to accomplish this.

The only parameter you should need to configure is the IP address.

## Functionality
This addon is not complete, initially I am implementing all functionality for the equipment that I have.  If you have equipmment or functionality that is not supported in the addon, please don't hesitate to [Open an Issue](https://github.com/cryptk/haomnilogic-local/issues)

- Filter Pumps
    - Turn on/off
    - Set speed to high/med/low presets
    - Set speed to custom value
- Lights
    - Turn on/off
    - Set brightness
    - Set show/effect
- Relays (Valve Actuators)
    - Turn on/off
- Sensors
    - Report state
- Heaters
    - Turn on/off
    - View current temperature
    - Adjust set temperature

## Credits

The work on this integration would not have been possible without the efforts of [djtimca](https://github.com/djtimca/) and [John Sutherland]