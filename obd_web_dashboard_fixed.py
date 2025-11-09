# ⚠️ Must come first for eventlet
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
import obd
import threading

# Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Connect to the OBD-II adapter
print("Connecting to OBD2 adapter...")
connection = obd.OBD("/dev/rfcomm0")  # adjust if your rfcomm device is different

# Commands to display on gauges
commands = {
    "RPM": obd.commands.RPM,
    "Speed": obd.commands.SPEED,
    "Coolant Temp": obd.commands.COOLANT_TEMP,
    "Throttle": obd.commands.THROTTLE_POS,
    "Fuel Level": obd.commands.FUEL_LEVEL,
}

# Background thread to emit live OBD data
def obd_thread():
    while True:
        data = {}
        for name, cmd in commands.items():
            response = connection.query(cmd)
            # Explicitly check for None to avoid Pint offset error
            if response.value is not None:
                try:
                    data[name] = float(response.value.magnitude)
                except:
                    data[name] = 0
            else:
                data[name] = 0
        socketio.emit("obd_data", data)
        socketio.sleep(1)

# Flask route for web page
@app.route("/")
def index():
    return render_template("dashboard.html")

# Start OBD background thread
threading.Thread(target=obd_thread, daemon=True).start()

# Run Flask server
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
