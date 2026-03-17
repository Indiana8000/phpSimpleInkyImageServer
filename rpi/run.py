#!/usr/bin/env python3
#
# phpSimpleInkyImageServer
#
# - Require Python 3.10 or newer
#
import time
import math
import requests
import os
import random

import RPi.GPIO as GPIO # type: ignore

from PIL import Image, ImageStat, ImageOps
from inky.auto import auto # type: ignore
from inky.inky_uc8159 import CLEAN # type: ignore

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from threading import Thread

# How long in minutes a image should be displayed
slideshow = 20

# Where to get the images: remote / local / wallhaven / deviantart
mode = "wallhaven"

# Local / Offline Parameters
image_path = "images"
image_history_max = 15

# Remote / Online Parameters
url_base = "http://192.168.5.21/inky" # You cound use the Demo site as source for testing: https://inky.bluepaw.de/
url_inky = url_base + "/api.php?action=inky"

# Wallhaven Parameters
wallhaven_apikey  = ""          # Your Wallhaven API key (required for nsfw purity=xx1)
wallhaven_purity  = "100"       # sfw=100, sketchy=010, nsfw=001 (or combinations, e.g. 111 = all)
wallhaven_ratios  = "16x9"      # e.g. 16x9, 16x10, 9x16
wallhaven_sorting = "random"    # date_added, relevance, random, views, favorites, toplist
wallhaven_query   = ""          # optional search term, leave empty for any

# DeviantArt Parameters  (create app at https://www.deviantart.com/developers/)
deviantart_client_id     = ""           # DeviantArt app client ID
deviantart_client_secret = ""           # DeviantArt app client secret
deviantart_tag           = "wallpaper"  # Tag to browse (browse/tags endpoint)
deviantart_mature        = False        # Include mature content (account must have it enabled)



# Internal Variables
image_history = []
image_last_name = ""
running = True
countdown = slideshow / 4

# DeviantArt token cache
_deviantart_token = None
_deviantart_token_expiry = 0.0

# Init Inky Display
inky = auto(verbose=True)
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

def getRandomImageWallhaven():
    global image_last_name
    params = {
        "purity":  wallhaven_purity,
        "ratios":  wallhaven_ratios,
        "atleast": "{}x{}".format(inky.resolution[0], inky.resolution[1]),
        "sorting": wallhaven_sorting,
        "q":       wallhaven_query,
        "apikey":  wallhaven_apikey,
    }
    # remove empty params so the API doesn't receive blank values
    params = {k: v for k, v in params.items() if v != ""}
    api_url = "https://wallhaven.cc/api/v1/search"
    response = requests.get(api_url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise ValueError("Wallhaven API returned no results")
    wallpaper = data[0]
    image_url = wallpaper["path"]
    image_last_name = image_url
    print("getRandomImageWallhaven - {}".format(image_url))
    r = requests.get(image_url, stream=True, timeout=30)
    r.raise_for_status()
    r.raw.decode_content = True
    return Image.open(r.raw)

def _getDeviantArtToken():
    global _deviantart_token, _deviantart_token_expiry
    if _deviantart_token and time.time() < _deviantart_token_expiry:
        return _deviantart_token
    r = requests.post(
        "https://www.deviantart.com/oauth2/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     deviantart_client_id,
            "client_secret": deviantart_client_secret,
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    _deviantart_token = data["access_token"]
    _deviantart_token_expiry = time.time() + data.get("expires_in", 3600) - 60
    return _deviantart_token

def getRandomImageDeviantArt():
    global image_last_name
    token = _getDeviantArtToken()
    headers = {"Authorization": "Bearer " + token}
    params = {
        "tag":            deviantart_tag,
        "limit":          50,
        "offset":         random.randint(1, 1000),
        "mature_content": "true" if deviantart_mature else "false",
    }
    api_url = "https://www.deviantart.com/api/v1/oauth2/browse/tags"
    response = requests.get(api_url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    results = response.json().get("results", [])
    # keep only image deviations that meet the display resolution
    min_w, min_h = inky.resolution
    images = [
        d for d in results
        if d.get("content")
        and d["content"].get("width",  0) >= min_w
        and d["content"].get("height", 0) >= min_h
    ]
    if not images:
        raise ValueError("DeviantArt API returned no suitable image results")
    image_url = random.choice(images)["content"]["src"]
    image_last_name = image_url
    print("getRandomImageDeviantArt - {}".format(image_url))
    r = requests.get(image_url, stream=True, timeout=30)
    r.raise_for_status()
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
        image = ImageOps.fit(image, resolution, method=Image.LANCZOS, centering=(0.5, 0.5))
    return image

def getSaturationByBrightness(image):
    stat = ImageStat.Stat(image)
    sat = math.sqrt(0.241*(stat.mean[0]**2) + 0.691*(stat.mean[1]**2) + 0.068*(stat.mean[2]**2))
    # Continuous linear interpolation: dark images -> 0.0, bright images -> max 0.7
    # The upper limit of 0.7 prevents results from appearing too bright / washed out on the display
    saturation = round(max(0.0, min(0.7, sat / 255.0 * 0.85)), 2)
    print("getSaturationByBrightness - sat:{:.1f} -> saturation:{:.2f}".format(sat, saturation))
    return saturation

# Show image on screen +Resize +Saturation
def showImage(image):
    image = image.convert("RGB")
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
            elif mode == "wallhaven":
                image = getRandomImageWallhaven()
            elif mode == "deviantart":
                image = getRandomImageDeviantArt()
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
# LABELS = ['A', 'B', 'C', 'D']
if inky.eeprom.display_variant == 21:
    BUTTONS = [5, 6, 25, 24]
else:
    BUTTONS = [5, 6, 16, 24]
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Register Events
GPIO.add_event_detect(BUTTONS[0], GPIO.FALLING, handle_buttonLoad    , bouncetime=300)
GPIO.add_event_detect(BUTTONS[1], GPIO.FALLING, handle_buttonLoad    , bouncetime=200)
GPIO.add_event_detect(BUTTONS[2], GPIO.FALLING, handle_buttonLikeit  , bouncetime=300)
GPIO.add_event_detect(BUTTONS[3], GPIO.FALLING, handle_buttonDisLike , bouncetime=300)

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
        qs = parse_qs(urlparse(self.path).query)
        action = qs.get("action", [None])[0]
        status = "Unknown Error"
        if action == 'clear':
            handle_buttonClear(0)
            status = "OK"
        elif action == 'next':
            handle_buttonLoad(2)
            status = "OK"
        elif action == 'status':
            status = '{"slideshow": %d, "countdown": %d, "running": "%s", "last_image": "%s"}' % (slideshow, countdown, running, image_last_name) 
        elif action == 'show':
            url = qs.get("url", [None])[0]
            if not url:
                status = "Missing url parameter."
            elif "@" in url:
                status = "Posible URL-Spoofing detected! Please remove all @ characters from your file names."
            else:
                handle_wwwLoad(url)
                status = "OK"

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(status, "utf-8"))
        #self.wfile.write(bytes("<html><head><title>phpSimpleInkyImageServer</title></head><body>", "utf-8"))
        #self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
        #self.wfile.write(bytes("</body></html>", "utf-8"))

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
