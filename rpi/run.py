#!/usr/bin/env python3
import time
import math
import requests
import os
import random

import RPi.GPIO as GPIO

from PIL import Image, ImageStat
from inky.auto import auto
from inky.inky_uc8159 import CLEAN

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# How long in minutes a image should be displayed
slideshow = 20

# Where to get the images: remote / local
mode = "remote"

# Local / Offline Parameters
image_path = "images"
image_history_max = 15

# Remote / Online Parameters
url_base = "http://192.168.5.21/inky/"
url_inky = url_base + "index.php?inky=1"



# Internal Variables
image_history = []
image_last_name = ""
running = True
countdown = slideshow / 4

# Init Inky Display
inky = auto(ask_user=True, verbose=True)
saturation = 0.5



def getRandomImageLocal():
    global image_history, image_last_name

    images = [f for f in os.listdir(image_path) 
              if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
    images_notseen = [p for p in images if p not in image_history]
    if not images_notseen:
        images_notseen = images
        image_history = []

    image = random.choice(images_notseen)
    image_history.append(image)
    if len(image_history) > image_history_max:
        image_history.pop(0)

    image_last_name = os.path.join(image_path, image)
    print("getRandomImageLocal - {}".format(image_last_name))
    return Image.open(image_last_name)

def getRandomImageRemote(pin):
    global image_last_name
    response = requests.get("{}&button={}&resx={}&resy={}".format(url_inky, pin, inky.resolution[0], inky.resolution[1]))
    print("getRandomImageRemote - {}".format(response.url))
    image_last_name = response.text
    print("getRandomImageRemote - {}".format(image_last_name))
    r = requests.get("{}/{}".format(url_base, image_last_name), stream=True)
    r.raw.decode_content = True
    return Image.open(r.raw)

def getImageRemote(image_url):
    global image_last_name
    image_last_name = image_url
    print("getImageRemote - {}".format(image_last_name))
    r = requests.get("{}/{}".format(url_base, image_last_name), stream=True)
    r.raw.decode_content = True
    return Image.open(r.raw)

# Resize Image by Aspection Ratio and Fill
def resizeImage(image, resolution):
    if image.size != resolution:
        aspection_ratio_target = resolution[0] / resolution[1]
        aspection_ratio_source = image.size[0] / image.size[1]
        if aspection_ratio_source < aspection_ratio_target:
            height = resolution[1] * image.size[0] / resolution[0]
            height = (image.size[1] - height) / 2
            box = (0, height, image.size[0], image.size[1] - height)
        else:
            width = resolution[0] * image.size[1] / resolution[1]
            width = (image.size[0] - width) / 2
            box = (width, 0, image.size[0] - width, image.size[1])
        print("resizeImage - {}@{:.2f} to {}@{:.2f}".format(image.size, aspection_ratio_source, resolution, aspection_ratio_target))
        resizedimage = image.resize(resolution, Image.LANCZOS, box)
    else:
        resizedimage = image.copy()
    return resizedimage

def getSaturationByBrightness(image):
    stat = ImageStat.Stat(image)
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
    return saturation

# Show image on screen +Resize +Saturation
def showImage(image):
    image = resizeImage(image, inky.resolution)
    saturation = getSaturationByBrightness(image)
    inky.set_image(image, saturation=saturation)
    inky.show()
    print("showImage - Done")

# Handler for Webserver to load image
def handle_wwwLoad(image_url):
    global countdown, running
    running = False
    countdown = slideshow / 2
    image = getImageRemote(image_url)
    showImage(image)
    running = True
    print("handle_wwwLoad - Done")

# Button handler loading
def handle_buttonLoad(pin):
    global countdown, running
    if countdown < slideshow:
        print("Button {} - Loading - Start - Mode: {}".format(pin, mode))
        running = False
        countdown = slideshow
        try:
            if mode == "local":
                image = getRandomImageLocal()
            else:
                image = getRandomImageRemote(pin)
            showImage(image)
        except Exception as e:
            print(f"An exception occurred: {type(e).__name__} – {e}")
        running = True
        print("Button {} - Loading - Done".format(pin))
    else:
        print("Button {} - Loading - Ignored!".format(pin))

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

# Button like
def handle_buttonLikeit(pin):
    print("Button {} - LikeIT - Start".format(pin))
    r = requests.get("{}&likeit=1&image={}".format(url_inky, image_last_name))
    print("Button {} - LikeIT - Done - {}".format(pin, r.url))

# Button dislike
def handle_buttonDisLike(pin):
    print("Button {} - DisLikeIT - Start".format(pin))
    r = requests.get("{}&likeit=-1&image={}".format(url_inky, image_last_name))
    print("Button {} - DisLikeIT - Done - {}".format(pin, r.url))

# Define GPIO Buttons
BUTTONS = [5, 6, 16, 24]
# LABELS = ['A', 'B', 'C', 'D']
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
            print("Countdown: ", countdown)
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
                handle_wwwLoad("./" + request[2] + "/" + request[3])
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
    print("Webserver started!")
    webServer.serve_forever()

# Main
if __name__ == "__main__":
    print("Starting main")
    thread_slideshow = Thread(target=slideshow_loop)
    thread_webserver = Thread(target=webserver_loop)
    thread_slideshow.start()
    thread_webserver.start()
