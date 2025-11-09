# obd_dashboard_app.py
# Must monkey_patch before importing other blocking/network libs.
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
import obd
import threading
import json
import os

APP_DIR = os.path.expanduser("~") + "/obd_dashboard"
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

app = Flask(__name__)
socketio = SocketIO(app)

# Connect to OBD adapter (adjust if your rfcomm path is different)
print("Connecting to OBD2 adapter...")
connection = obd.OBD("/dev/rfcomm0")  # None if failed; code handles that.

# Define available commands.
# Keys must be safe for HTML ids (no spaces). Values are (display name, obd command)
ALL_COMMANDS = {
    "RPM":             ("RPM", obd.commands.RPM),
    "Speed":           ("Speed", obd.commands.SPEED),
    "CoolantTemp":     ("Coolant Temp", obd.commands.COOLANT_TEMP),
    "Throttle":        ("Throttle", obd.commands.THROTTLE_POS),
    "FuelLevel":       ("Fuel Level", obd.commands.FUEL_LEVEL),
    "IntakeTemp":      ("Intake Temp", obd.commands.INTAKE_TEMP),
    "MAF":             ("MAF", obd.commands.MAF),
    # Add more as needed: "Key": ("Display Name", obd.commands.SOME_CMD)
}

# Default selections (Enable by default)
def default_selections():
    return {k: "Enable" for k in ALL_COMMANDS.keys()}

# Load / save functions for persistence
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return default_selections()
    else:
        return default_selections()

def save_config(cfg):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Error saving config:", e)

selected_gauges = load_config()

# Background thread: query enabled gauges and emit via SocketIO
def obd_thread():
    while True:
        if connection.is_connected():
            data = {}
            for key, status in selected_gauges.items():
                if status == "Enable":
                    _, cmd = ALL_COMMANDS[key]
                    try:
                        response = connection.query(cmd, timeout=1.0)
                        # response.value can be a Pint Quantity. Check explicitly.
                        if response and response.value is not None:
                            try:
                                val = float(response.value.magnitude)
                            except Exception:
                                # fallback if magnitude missing or not numeric
                                try:
                                    val = float(response.value)
                                except:
                                    val = 0.0
                        else:
                            val = 0.0
                    except Exception:
                        val = 0.0
                    data[key] = val
            if data:
                socketio.emit("obd_data", data)
        else:
            # If not connected, emit zeros for enabled gauges to keep front-end stable
            data = {}
            for key, status in selected_gauges.items():
                if status == "Enable":
                    data[key] = 0.0
            if data:
                socketio.emit("obd_data", data)
        socketio.sleep(1)

# Start background thread
threading.Thread(target=obd_thread, daemon=True).start()

# Routes
@app.route("/")
def index():
    return redirect(url_for("setup"))

@app.route("/setup", methods=["GET", "POST"])
def setup():
    global selected_gauges
    if request.method == "POST":
        # For each command key, read posted selection
        for key in ALL_COMMANDS.keys():
            # default to "Not applicable" if nothing posted
            val = request.form.get(key, "Not applicable")
            if val not in ("Enable", "Disable", "Not applicable"):
                val = "Not applicable"
            selected_gauges[key] = val
        save_config(selected_gauges)
        return redirect(url_for("dashboard"))
    # render setup page with display names and current selections
    display_list = [(k, ALL_COMMANDS[k][0]) for k in ALL_COMMANDS.keys()]
    return render_template("setup.html", commands=display_list, selections=selected_gauges)

@app.route("/dashboard")
def dashboard():
    # Only show enabled gauges (pass keys and display names)
    enabled = [(k, ALL_COMMANDS[k][0]) for k, s in selected_gauges.items() if s == "Enable"]
    return render_template("dashboard_dynamic.html", commands=enabled)

if __name__ == "__main__":
    # make sure config dir exists
    os.makedirs(APP_DIR, exist_ok=True)
    socketio.run(app, host="0.0.0.0", port=5000)
