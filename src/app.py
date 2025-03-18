from flask import Flask, render_template, request, redirect, url_for,  jsonify
from signal import SIGINT
import webview as pywebview
from pystray import Icon, MenuItem, Menu
from PIL import Image
import requests
import threading
import time
from miner import Miner
import os
import logging

if os.name == 'nt':  # For Windows
    app_data_dir = os.path.join(os.environ['APPDATA'], 'Xylume Miner')
else:  # For macOS and Linux
    app_data_dir = os.path.expanduser('~/.local/share/XylumeMiner')
os.makedirs(app_data_dir, exist_ok=True)
miner_address_file = os.path.join(app_data_dir, 'xyl_miner_address')

app = Flask(__name__)
app.secret_key = os.urandom(24)

log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True
logging.getLogger('werkzeug').setLevel(logging.WARNING) 

miner_address = 'network_miner'
miner_running = False
mining_thread = None
traversalspeed = 0 # txs checked per second
lastsubmissionerror, accepted, rejected = None, 0, 0
rpc_url = ''

miner = Miner(rpc_url, miner_address)

key_env = os.getenv('XYL_TESTMINER_ADDRESS')
if key_env is None:
    os.system(f'setx XYL_TESTMINER_ADDRESS "{key}"')
else:
    key = key_env

def mine():
    global miner_address, miner_running
    miner.set_data(rpc_url, miner_address)
    while miner_running:
        miner.mine()
        time.sleep(1)

@app.route("/")
def home():
    global miner_address, miner_running
    if os.path.exists(miner_address_file):
        miner_address = open(miner_address_file, "r").read().strip()
        miner.set_data(rpc_url, miner_address)
    return render_template("index.html", miner_running=miner_running)

@app.route("/start", methods=["POST"])
def start_miner():
    global miner_running, mining_thread
    if not miner_running:
        miner_running = True
        mining_thread = threading.Thread(target=mine, daemon=True)
        mining_thread.start()
        return jsonify({"status": "Miner started."})
    return jsonify({"status": "Miner is already running."})

@app.route("/stop", methods=["POST"])
def stop_miner():
    global miner_running
    if miner_running:
        miner_running = False
        return jsonify({"status": "Miner stopped."})
    return jsonify({"status": "Miner is not running."})

@app.route('/get_speed', methods=['GET']) # traversal speed
def getspeed():
    return jsonify({"speed": traversalspeed})

@app.route('/set_speed', methods=['POST'])
def setspeed():
    global traversalspeed
    traversalspeed = round(request.get_json().get('speed'), 2) or 0.0
    return jsonify({"status": "Updated speed"})

@app.route('/get_submissions', methods=['GET']) # traversal speed
def getsubmissions():
    global lastsubmissionerror
    lasterror = lastsubmissionerror
    lastsubmissionerror = None
    return jsonify({"accepted": accepted, "rejected": rejected, "last": lasterror})

@app.route('/set_submissions', methods=['POST'])
def setsubmissions():
    global lastsubmissionerror, accepted, rejected
    if request.get_json().get('code') == 200:
        accepted += 1
    else:
        rejected += 1
        lastsubmissionerror = request.get_json().get('message')
    return jsonify({"status": "Success."})

@app.route('/node', methods=['POST']) # to set new node url
def setnode():
    global rpc_url
    rpc_url = request.get_json().get('node')
    miner.set_data(rpc_url, miner_address)
    return jsonify({"status": "Success."})

@app.route('/address', methods=['POST']) # to set new address
def setaddress():
    global miner_address
    miner_address = request.get_json().get('address')
    miner.set_data(rpc_url, miner_address)
    return jsonify({"status": "Success."})

@app.route('/minimize', methods=['POST'])
def minimize_window():
    window.minimize()
    return jsonify({"status": "Window minimized"})

@app.route('/close', methods=['POST'])
def close_window():
    window.hide()
    return jsonify({"status": "App closing..."})

def run():
    app.run(host='0.0.0.0',port=3469, threaded=True)

def stop_flask():
    os.kill(os.getpid(), SIGINT)

def keep_alive():
  t = threading.Thread(target=run)
  t.start()

def systray():
    global icon, window
    icon_image = Image.open(requests.get("https://raw.githubusercontent.com/debxylen/XylumeMiner/refs/heads/main/icon.png", stream=True).raw)  # image for the tray icon
    icon = Icon("Xylume Miner", icon_image)

    def on_show(icon, item):
        window.show()
    def stop_all(icon, item):
        stop_flask()
        window.destroy()
        icon.stop()
    icon.menu = Menu(MenuItem("Open", on_show, default=True), MenuItem("Quit", stop_all))
    icon.run_detached()

window = pywebview.create_window('Xylume Miner', 'http://127.0.0.1:3469', maximized=True, fullscreen=False, frameless=True, background_color='#111827', resizable=True, easy_drag=True)
keep_alive()
systray()
pywebview.start()

