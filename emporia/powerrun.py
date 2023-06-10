import emporia
import time
from umqtt.simple import MQTTClient
import json
import machine
import config

led = machine.Pin(23, machine.Pin.OUT)
lasterror=None
z=None

def init():
    global z
    z = MQTTClient(config.mqtt_name,config.mqtt_addr,1883,config.mqtt_name,config.mqtt_pass)
    z.connect()
 
def processPower():
    j = emporia.getJson()
    jj = json.dumps(j)
    if z == None:
        init()
    z.publish("powermon",jj)

def flash(cnt):
    while True:
        led.value(1)
        time.sleep_ms(200)
        led.value(0)
        cnt-=1
        if cnt<=0:
            break
        time.sleep_ms(200)

def runner():
    global z
    while True:
        try:
            processPower()
        except Exception as e:
            flash(5)
            lasterror=e
            time.sleep(1)
            z=None
        flash(1)
        time.sleep(10)
