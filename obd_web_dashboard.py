# obd_web_dashboard.py
# Fixed version: eventlet monkey_patch applied first, app context properly handled

import eventlet
eventlet.monkey_patch()  # MUST be first

from flask import Flask, render_template
from flask_socketio import SocketIO
import obd
import threading
import time

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Connect to OBD-II adapter
connection = obd.OBD()  # defaults to auto-detect

# Background thread to read OBD data
def obd_thread():
    with app.app_context():  # Ensure Flask app context is active
        while True:
            if connection.is_connected():
                rpm_response = connection.query(obd.commands.RPM)
                speed_response = connection.query(obd.commands.SPEED)

                rpm = rpm_response.value.magnitude if rpm_response.value else 0
                speed = speed_response.value.to("mph").magnitude if speed_response.value else 0

                # Emit data to all connected clients
                socketio.emit('obd_data', {'rpm': rpm, 'speed': speed})

            socketio.sleep(0.5)  # Eventlet-friendly sleep

# Route for main dashboard page
@app.route('/')
def index():
    return render_template('setup.html')

# Start background thread when first client connects
@socketio.on('connect')
def handle_connect():
    if not hasattr(app, 'obd_thread_started'):
        thread = threading.Thread(target=obd_thread)
        thread.daemon = True
        thread.start()
        app.obd_thread_started = True

# Run Flask app with SocketIO
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
