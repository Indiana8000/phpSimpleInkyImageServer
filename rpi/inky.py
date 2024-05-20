#!/usr/bin/env python3

import sys
import time
import signal
import io
import math
import requests
import RPi.GPIO as GPIO

from PIL import Image, ImageStat
from inky.auto import auto
from inky.inky_uc8159 import CLEAN

# Parameters
url = "http://192.168.5.21/inky/image.php?inky=1"
slideshow = 60

# Variables
running = True
countdown = slideshow / 4

# Init Display
inky = auto(ask_user=True, verbose=True)
saturation = 0.5

# Set GPIO Buttons
BUTTONS = [5, 6, 16, 24]
LABELS = ['A', 'B', 'C', 'D']
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Determine image brightness
def brightness(im):
    stat = ImageStat.Stat(im)
    r,g,b = stat.mean
    sat = math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))
    saturation = 0.5
    if sat < 100:
        saturation = 0.25
    if sat < 40:
        saturation = 0.0
    if sat > 140:
        saturation = 0.75
    if sat > 180:
        saturation = 1.0
    print("Brightness: {} = {}".format(sat, saturation))
    return saturation

# Button generic handler
def handle_button(pin):
    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))

# Inky Clear Screen
def handle_buttonClear(pin):
    global running
    print("Button {} - Clear Start".format(pin))
    running = False
    for _ in range(2):
        for y in range(inky.height - 1):
            for x in range(inky.width - 1):
                inky.set_pixel(x, y, CLEAN)
        inky.show()
        time.sleep(1.0)
    running = True
    print("Button {} - Clear Done".format(pin))

# Button handler loading
def handle_buttonLoad(pin):
    global countdown
    print("Button {} - Loading Start".format(pin))
    running = False
    countdown = slideshow
    r = requests.get("{}&button={}".format(url, pin), stream=True)
    r.raw.decode_content = True
    image = Image.open(r.raw)
    resizedimage = image.resize(inky.resolution)
    saturation = brightness(resizedimage)
    inky.set_image(resizedimage, saturation=saturation)
    print("Button {} - Got Image".format(pin))
    inky.show()
    running = True
    print("Button {} - Loading Done".format(pin))

def handle_buttonLikeit(pin):
    print("Button {} - LikeIT Start".format(pin))
    r = requests.get("{}&likeit=1".format(url), stream=True)
    print("Button {} - LikeIT Done".format(pin))

def handle_buttonDisLike(pin):
    print("Button {} - DisLikeIT Start".format(pin))
    r = requests.get("{}&likeit=-1".format(url), stream=True)
    print("Button {} - DisLikeIT Done".format(pin))

GPIO.add_event_detect( 5, GPIO.FALLING, handle_buttonLoad    , bouncetime=250)
GPIO.add_event_detect( 6, GPIO.FALLING, handle_buttonLoad    , bouncetime=250)
GPIO.add_event_detect(16, GPIO.FALLING, handle_buttonLikeit  , bouncetime=250)
GPIO.add_event_detect(24, GPIO.FALLING, handle_buttonDisLike , bouncetime=250)

print("Starting ...")
while True:
    if running:
        countdown = countdown - 1
        print("Countdown:", countdown)
    if countdown <= 0:
        handle_buttonLoad(1)
    time.sleep(60.0)

# END