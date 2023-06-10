# Emporia Vue
 
MicroPython projects for the Emporia Vue

## Emporia
This runs on the ESP32 on the Emporia Vue.

Flashed with MicroPython.

the emporia.py module reads the i2c data, and unpacks the data into a dictionay/structure

the powermon read the data in a loop and sends to a MQTT server

## SWD
AMD-SWD impementation

Read/write flash/ram using the existing SWD connection between the EPS32 and teh SAMD09

