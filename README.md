# Plant Monitor Plus Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Downloads][download-latest-shield]]()
[![License][license-shield]](LICENSE)

Plant Monitor Plus is an integration to give details of a plant's moisture with a problem sensor when it requires attention and a last watered tracker that you can automatically (or manually) record when the plant was last watered.

When you configure each plant, you provide a physical moisture sensor and set thresholds for minimum, maximum, and amount of moisture increase to detect a plant has been watered.
You can adjust these at any time via the UI.

The last watered will not immediately change based on the current moisture value, but instead use a sliding window to both detect gradual increases when watered.

## Entities

### Moisture status
A binary problem sensor indicating if there is a problem that needs addressing with attributes giving detailed information.

### Watered
A button to manually update the plant as having been watered.

### Last watered
A sensor indicating the last time the plant was watered, updated by either automatic detection (if an increase threshold is set), a manual button press, or the set plant watered action.

### Moisture+
A sensor that mirrors the current moisture value but adding attributes for configuration and state for the device, intended for easy use within dashboards.

## Actions

### Get plant summary

Get details of all plants and what requires attention, which you can call at convenient times to send notifications, etc.

### Set plant watered

Provides a way to set a plant as having been watered, either now or at a specific date.

### Set plant thresholds

Updates a plant's thresholds, useful for seasonal adjustment automations.

_Please :star: this repo if you find it useful_

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)


![Device Creation](https://raw.githubusercontent.com/andrew-codechimp/HA-Plant-Monitor-Plus/main/images/configuration.png "Device Creation")

![Device Entities](https://raw.githubusercontent.com/andrew-codechimp/HA-Plant-Monitor-Plus/main/images/device.png "Device Entities")

## Example plant summary automation

```
alias: Plant monitor moisture notification
description: "Display a notification showing plants that need watering"
triggers:
  - trigger: time
    at: "08:30:00"
conditions: []
actions:
  - action: plant_monitor_plus.get_plant_summary
    metadata: {}
    data: {}
    response_variable: plant_action_response
  - variables:
      plantsensors: "{{plant_action_response['too_dry'] | join(', ')}}"
  - if:
      - condition: template
        value_template: "{{ plantsensors != '' }}"
    then:
      - action: persistent_notification.create
        metadata: {}
        data:
          message: "Low moisture warning for: {{plantsensors}}"
mode: single
```

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrew-codechimp&repository=HA-Plant-Monitor-Plus&category=Integration)

This is a HACS custom integration; if the link does not work, you will have to add this repository URL via HACS custom repositories.

## FAQ's

* Why only moisture?
I used the default Plant Monitor YAML based integration for a long time and never found the other sensors useful. There are plenty of other plant integrations available if you require more than just moisture.

* Why no dashboard card?
I primarily created this integration to provide notifications and since they are standard sensor/binary sensor entities there are plenty of cards available that can be used.


[commits-shield]: https://img.shields.io/github/commit-activity/y/andrew-codechimp/HA-Plant-Monitor-Plus.svg?style=for-the-badge
[commits]: https://github.com/andrew-codechimp/HA-Plant-Monitor-Plus/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/andrew-codechimp/HA-Plant-Monitor-Plus.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/andrew-codechimp/HA-Plant-Monitor-Plus.svg?style=for-the-badge
[releases]: https://github.com/andrew-codechimp/HA-Plant-Monitor-Plus/releases
[download-latest-shield]: https://img.shields.io/github/downloads/andrew-codechimp/HA-Plant-Monitor-Plus/latest/total?style=for-the-badge
[hacs-installs-shield]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fplant_monitor_plus&style=for-the-badge
