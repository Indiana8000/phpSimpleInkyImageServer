# phpSimpleInkyImageServer
A simple python + php script to supply your [Pimoroni Inky e-paper](https://shop.pimoroni.com/products/inky-impression-7-3) with images

## Features
- Change the image every X minutes
- Mark current image as favorit (like / dislike)
- Remote control your inky (Next random image / One sepcific from your list)
- Support SQLite (default) and MySQL (Recommended if you have more than ~500 images)

## Installation
1. Copy index.php to any Webserver (e.g. your NAS)
    - Optional: Change config in index.php to use mysql
2. Copy run.py to your inky setup
    - [Pimoroni - Combined Python library](https://github.com/pimoroni/inky) or checkout the Tutorial [Pimoroni - Getting Started with Inky Impression](https://learn.pimoroni.com/article/getting-started-with-inky-impression)
    - Optional: see cronjob.example for autostart