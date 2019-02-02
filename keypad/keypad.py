#!/usr/bin/python
#
from evdev import InputDevice, categorize, ecodes
import sys
import socket
import psutil
from time import sleep
import paho.mqtt.client as mqtt
import json
import threading
import signal
import time
import os
import pyttsx

tts = pyttsx.init()


os.system("/usr/bin/aplay /root/pi-alarm/keypad/system-started.wav")


HOST = 'xx.xx.xx.xx'
PORT = 1883

device = InputDevice("/dev/input/event0") # my keyboard

digits = { 82, 79, 80, 81, 75, 76, 77, 71, 72, 72, 73 }

chars = {} 
running = 1
speak = ""
open_list = ""

for i in range(0,100):
    chars[i] = -1

chars[82] = '0'
chars[79] = '1'
chars[80] = '2'
chars[81] = '3'
chars[75] = '4'
chars[76] = '5'
chars[77] = '6'
chars[71] = '7'
chars[72] = '8'
chars[73] = '9'

pin = ""

def on_connect(mosq, obj, rc):
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    global message
    global speak
    global open_list

    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    pl = json.loads(msg.payload)
    status = pl["status"]
    open_list = pl["open_list"]
    next = pl["next_state"]
    print("status: " + status + ", next:" + next)
    if status == "unset":
        print("OK")
    elif status == "set":
        print("Set")
    elif status == "alarm":
        print("Alarm")
    elif status == "set_fail":
        print("Set Fail")
    else:
        # It's a digit, beep the buzzer
        print("Beep")
        os.system("/usr/bin/aplay /root/pi-alarm/keypad/beep.wav")
    if status != next:
	speak = next
    message = msg.payload

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

 
mqttc = mqtt.Client()

mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

mqttc.connect(HOST, PORT,60)


cpu_pc = psutil.cpu_percent()
print cpu_pc
cpu_temp = round(int(open('/sys/class/thermal/thermal_zone0/temp').read()) / 1e3,1)


rc = mqttc.loop()
mqttc.subscribe("alarm_status")


def send_pin(pin):
    global frame

    frame = '{ ';
    frame += '"pin_code":' + pin + ', '
    frame += '"cpu_temp":' + str(round(cpu_temp,2))+ ', '
    frame += '"cpu_pc":' + str(round(cpu_pc,2))
    frame += ' }';

    print frame

    mqttc.publish("alarm_pin",frame)

    print("rc: " + str(rc))



def keyboard_handler():
    global pin
    global running
    global device

    device.grab()

    while running:
        if running == 0:
            print("Keyboard Thread Exiting...")
            device.ungrab()
            return
        event = device.read_one()
        if event:
            if event.type == ecodes.EV_KEY and event.value == 1:
                os.system("/usr/bin/aplay /root/pi-alarm/keypad/pip.wav")
                print(categorize(event))
    
                if event.code in digits:
                    #print("It's a digit - " + chars[event.code])
                    pin = pin + chars[event.code]
    
                if event.code == 83:  # Del
                    pin = pin[:-1]
    
                if event.code == 78:  # + Set
                    print("Setting with pin [" + pin + "]")
                    send_pin(pin)
                    pin = ""
    
                if event.code == 74:  # = Unset
                    print("Unsetting with pin [" + pin + "]")
                    send_pin(pin)
                    pin = ""
    
                print(pin)
    


def sigint_handler(signum, frame):
    global running
    running = 0
 

signal.signal(signal.SIGINT, sigint_handler)

t = threading.Thread(target=keyboard_handler)
t.start()

while running:
    sleep(0.1)
    rc = mqttc.loop()
    if speak == "unset":
        os.system("/usr/bin/aplay /root/pi-alarm/keypad/system-unset.wav")
        speak = ""
    if speak == "setting":
        os.system("/usr/bin/aplay /root/pi-alarm/keypad/system-arming.wav")
        speak = ""
    if speak == "set":
        os.system("/usr/bin/aplay /root/pi-alarm/keypad/system-armed.wav")
        speak = ""
    if speak == "set_fail":
        os.system("/usr/bin/aplay /root/pi-alarm/keypad/failed-active-sensors.wav")
        tts.say(open_list)
        tts.runAndWait()

print("Main Thread Exited")


t.join()

mqttc.disconnect()

