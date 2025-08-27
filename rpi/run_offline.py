#!/usr/bin/env python3
import os
import time
import math
import random

import RPi.GPIO as GPIO

from PIL import Image, ImageStat
from inky.auto import auto
from inky.inky_uc8159 import CLEAN

# Parameters
slideshow = 60

# Variables
running = True
countdown = slideshow / 4

# Verzeichnis mit den Bildern
BILDER_VERZEICHNIS = "images"
letzte_auswahl = []

def zufaelliges_bild():
    global letzte_auswahl

    bilder = [f for f in os.listdir(BILDER_VERZEICHNIS) 
              if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
    verfuegbar = [b for b in bilder if b not in letzte_auswahl]
    if not verfuegbar:
        verfuegbar = bilder
        letzte_auswahl = []

    # Zufällige Auswahl
    bild = random.choice(verfuegbar)
    letzte_auswahl.append(bild)
    if len(letzte_auswahl) > 15:
        letzte_auswahl.pop(0)

    return os.path.join(BILDER_VERZEICHNIS, bild)

# Init Inky Display
inky = auto(ask_user=True, verbose=True)
saturation = 0.5

# Define GPIO Buttons
BUTTONS = [5, 6, 16, 24]
LABELS = ['A', 'B', 'C', 'D']
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Button generic handler
def handle_button(pin):
    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))

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
    #print("Brightness: {} = {}".format(sat, saturation))
    return saturation

# Inky Clear Screen
def handle_buttonClear(pin):
    global countdown, running
    print("Button {} - Clear - Start".format(pin))
    running = False
    countdown = 1
    for _ in range(2):
        for y in range(inky.height - 1):
            for x in range(inky.width - 1):
                inky.set_pixel(x, y, CLEAN)
        inky.show()
        time.sleep(1.0)
    running = True
    print("Button {} - Clear - Done".format(pin))

# Button handler loading
def handle_buttonLoad(pin):
    global countdown, running
    if countdown < slideshow:
        print("Button {} - Loading - Start".format(pin))
        running = False
        countdown = 2
        try:
            image = Image.open(zufaelliges_bild())
            if image.size != inky.resolution:
                # Resize Image by Aspection Ratio
                aspection_ratio_target = inky.resolution[0] / inky.resolution[1]
                aspection_ratio_source = image.size[0] / image.size[1]
                if aspection_ratio_source < aspection_ratio_target:
                    height = inky.resolution[1] * image.size[0] / inky.resolution[0]
                    height = (image.size[1] - height) / 2
                    box = (0, height, image.size[0], image.size[1] - height)
                else:
                    width = inky.resolution[0] * image.size[1] / inky.resolution[1]
                    width = (image.size[0] - width) / 2
                    box = (width, 0, image.size[0] - width, image.size[1])
                resizedimage = image.resize(inky.resolution, Image.LANCZOS, box)
            else:
                resizedimage = image.copy()
            # Calculate Saturation
            saturation = brightness(resizedimage)
            inky.set_image(resizedimage, saturation=saturation)
            print("Button {} - Loading - Got Image".format(pin))
            inky.show()
            countdown = slideshow
        except:
            print("Connection Error")
        running = True
        print("Button {} - Loading - Done".format(pin))
    else:
        print("Button {} - Loading - Ignored!".format(pin))

# Register Events
GPIO.add_event_detect( 5, GPIO.FALLING, handle_buttonLoad , bouncetime=300)
GPIO.add_event_detect( 6, GPIO.FALLING, handle_buttonLoad , bouncetime=200)
GPIO.add_event_detect(16, GPIO.FALLING, handle_buttonLoad , bouncetime=300)
GPIO.add_event_detect(24, GPIO.FALLING, handle_buttonClear, bouncetime=300)

# Main Loop
if __name__ == "__main__":
    while True:
        if running:
            countdown = countdown - 1
            print("Countdown:", countdown)
            if countdown <= 0:
                handle_buttonLoad(1)
        time.sleep(60)
