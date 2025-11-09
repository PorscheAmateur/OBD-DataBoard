# obd_web_dashboard.py

import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import obd  # python-OBD

# -------------------------------
# Explicit OBD-II connection setup
# -------------------------------
OBD_DEVICE = "/dev/rfcomm0"

print(f"Connecting to OBD2 adapter on {OBD_DEVICE}...")
connection = obd.OBD(OBD_DEVICE)  # explicitly use your device

if connection.is_connected():
    print("Connected to OBD-II adapter!")
else:
    print("Failed to connect to OBD-II adapter. Check connection.")

# -------------------------------
# Flask app setup
# -------------------------------
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# -------------------------------
# OBD-II polling function
# -------------------------------
def safe_value(resp):
    """Safely extract magnitude from OBD response or return 'No Data'."""
    try:
        if resp.value is None:
            return "No Data"
        return resp.value.magnitude
    except Exception as e:
        return "No Data"

def poll_obd_data():
    while True:
        if connection.is_connected():
            try:
                rpm_resp = connection.query(obd.commands.RPM)
                speed_resp = connection.query(obd.commands.SPEED)
                coolant_resp = connection.query(obd.commands.COOLANT_TEMP)

                rpm = safe_value(rpm_resp)
                speed = safe_value(speed_resp)
                coolant = safe_value(coolant_resp)

                # Debug print
                print(f"Sending OBD data -> RPM: {rpm}, Speed: {speed}, Coolant: {coolant}")

                # Emit to the web dashboard via SocketIO
                socketio.emit("obd_data", {
                    "rpm": rpm,
                    "speed": speed,
                    "coolant_temp": coolant
                })

            except Exception as e:
                print(f"Error reading OBD data: {e}")

        time.sleep(1)  # adjust polling rate here

# Start OBD-II polling in a separate thread
threading.Thread(target=poll_obd_data, daemon=True).start()

# -------------------------------
# Flask routes
# -------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/dashboard_dynamic")
def dashboard_dynamic():
    return render_template("dashboard_dynamic.html")

@app.route("/dashboard_needle")
def dashboard_needle():
    return render_template("dashboard_needle.html")

# -------------------------------
# Main entry
# -------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
