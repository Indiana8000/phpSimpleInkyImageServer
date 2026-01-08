# phpSimpleInkyImageServer
A simple python and php script to supply your [Pimoroni Inky e-paper](https://shop.pimoroni.com/products/inky-impression-7-3) with images.

Now with a nice web UI! Demo available at https://inky.bluepaw.de/

## Features
- Change the image every X minutes
- Mark current image as favorit (like / dislike)
- Remote control your inky (Next random image / One sepcific from your list)
- Support SQLite (default) and MySQL (Recommended if you have more than ~500 images)

## Installation
1. Copy all files from "web" to any Webserver (e.g. your NAS)
    - Rename config.php.dist to config.php and check the settings inside.
    - Optional: If you don't want the web UI, just copy api.php and config.php

2. Copy run.py to your inky setup
    - [Pimoroni - Combined Python library](https://github.com/pimoroni/inky) or checkout the Tutorial [Pimoroni - Getting Started with Inky Impression](https://learn.pimoroni.com/article/getting-started-with-inky-impression)
    - Check first lines of run.py for configuration.
    - Optional: See cronjob.example for autostart.