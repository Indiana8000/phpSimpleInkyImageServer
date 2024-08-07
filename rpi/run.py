#!/usr/bin/env python3
import time
import math
import requests

import RPi.GPIO as GPIO

from PIL import Image, ImageStat
from inky.auto import auto
from inky.inky_uc8159 import CLEAN

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# Parameters
url_base = "http://192.168.5.21/inky/"
url_inky = url_base + "index.php?inky=1"
slideshow = 60

# Variables
running = True
countdown = slideshow / 4

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

def loadImage(path):
    global countdown, running
    running = False
    countdown = slideshow / 2
    r = requests.get(url_base + path, stream=True)
    r.raw.decode_content = True
    image = Image.open(r.raw)
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
    inky.show()
    running = True

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
    if countdown < (slideshow - 1):
        print("Button {} - Loading - Start".format(pin))
        running = False
        countdown = slideshow
        r = requests.get("{}&button={}".format(url_inky, pin), stream=True)
        r.raw.decode_content = True
        image = Image.open(r.raw)
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
        running = True
        print("Button {} - Loading - Done".format(pin))
    else:
        print("Button {} - Loading - Ignored!".format(pin))

# Button like
def handle_buttonLikeit(pin):
    print("Button {} - LikeIT - Start".format(pin))
    r = requests.get("{}&likeit=1".format(url_inky), stream=True)
    print("Button {} - LikeIT - Done".format(pin))

# Button dislike
def handle_buttonDisLike(pin):
    print("Button {} - DisLikeIT - Start".format(pin))
    r = requests.get("{}&likeit=-1".format(url_inky), stream=True)
    print("Button {} - DisLikeIT - Done".format(pin))

# Register Events
GPIO.add_event_detect( 5, GPIO.FALLING, handle_buttonLoad    , bouncetime=300)
GPIO.add_event_detect( 6, GPIO.FALLING, handle_buttonLoad    , bouncetime=200)
GPIO.add_event_detect(16, GPIO.FALLING, handle_buttonLikeit  , bouncetime=300)
GPIO.add_event_detect(24, GPIO.FALLING, handle_buttonDisLike , bouncetime=300)

# Slideshow Thread
def slideshow_loop():
    global countdown, running
    while True:
        if running:
            countdown = countdown - 1
            print("Countdown:", countdown)
            if countdown <= 0:
                handle_buttonLoad(1)
        time.sleep(60)

# Web Server Class
class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>phpSimpleInkyImageServer</title></head><body>", "utf-8"))
        self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
        request = self.path.split("/")
        if len(request) > 2:
            self.wfile.write(bytes("<p>Action: "+request[1]+"</p>", "utf-8"))
            if request[1] == "show":
                self.wfile.write(bytes("<p>Parameter: "+request[2]+"</p>", "utf-8"))
                self.wfile.write(bytes("<p>Parameter: "+request[3]+"</p>", "utf-8"))
                loadImage(request[2] + "/" + request[3])
            if request[1] == "clear":
                handle_buttonClear(0)
            if request[1] == "next":
                handle_buttonLoad(2)
        else:
            self.wfile.write(bytes("<p>Action: none</p>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))

# Web Server Thread
def webserver_loop():
    webServer = HTTPServer(("", 8080), MyServer)
    print("Server started http://%s:%s" % ("", 8080))
    webServer.serve_forever()

# Main
print("Starting ...")
thread_slideshow = Thread(target=slideshow_loop)
thread_webserver = Thread(target=webserver_loop)
thread_slideshow.start()
thread_webserver.start()
# END