# moes-bekn [![Made for ESPHome](https://img.shields.io/badge/Made_for-ESPHome-black?logo=esphome)](https://esphome.io)

This [ESPHome](https://esphome.io) package enables local MoesGo dimmers and switches that normally work through Tuya centralized servers. It creates light control entities in Home Assistant to control and monitor these devices. This package provides more detailed and operation than Home Assistant cloud based Tuya controls.

<!-- markdownlint-capture -->
<!-- markdownlint-disable -->
<p float="left">
    <img src="./img/ha_screen.png?raw=true" alt="Example Home Assistant device controls and sensors for an ESPHome-econet device." width=40%>
    <img src="./img/esphome_screen.png?raw=true" alt="esphome web UI screen" width=50%>
</p>

<!-- markdownlint-restore -->

## Supported / Tested MoesGo Hardware

Any MoesGo dimmers that use CB2 module should work. Most recently it was tested and confirmed working with [MOES Dual Dimmer Switch, Double Dimmer Switch for LED Lights, Full Range Dimming, WiFi Smart Light Switch Neutral Wire Required, Single Pole, 300W INC, 75W LED/CFL, Smart Life/Tuya APP Remote Control](https://www.amazon.com/dp/B0B971DJDF) purchased on Amazon.

## Prepare for flashing

In order to flash esphome on MoesGo, you will need a USB/TTL serial adapter. There is plenty of options on Amazon and Aliexpress. I've been using [this adapter](https://www.amazon.com/dp/B075N82CDL) for the last few years with no issues.

Unfortunately, MoesGo does not have pins or connectors on the board for dupont or other ways to connect the USB/TTL serial adapter. Soldering is required. The picture below shows the key connection and soldering points

![esphome web UI screen](./img/CB2_Connections.png?raw=true)

TX and RX pins are under the CB2 module, but there is just a little bit of PCB copper sticking out to solder on two thin wires.

The USB/TTL adapter connection is pretty typical:

| MoesGo Board Pin | Adapter Pin      |
|------------------|------------------|
| VCC              | VCC              |
| GND              | Ground           |
| RX               | TX               |
| TX               | RX               |

CEN - solder a wire and, optionally, add a switch connected to the ground. That is necessary for resetting the MCU - connecting the CEN to the ground triggers MCU reset.

## Software Installation

Copy the included secrets.yaml.sample to secrets.yaml

```console
cp secrets.yaml.sample secrets.yaml
```

Modify the contents of secrets.yaml to match your Wifi network SSID/password and also set the name and password for the backup Wifi in AP mode if the connection fails (this is a typical esphome setup).

Once the hardware and secrents.yaml are set up, you are ready to compine and install esphome using the standard esp run command

```console
esphome run moes_beken.yml
```

Once compiled and lined, esphome will prompt for the path to USB/Serial device, something like /dev/tty.usbserialXXXX

### Testing Local Changes

The esphome CLI can be used to compile and install changes to YAML and/or code via the `esphome config|compile|run` commands. You can use the `esphome config moes_beken.yml` command to see the results of any config updates, or the `esphome run moes_beken.yml` command to deploy your changes to an ESPHome-capable device over Wi-Fi or USB.
