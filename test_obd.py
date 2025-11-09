import obd
import time

print("Connecting to OBD2 adapter on /dev/rfcomm0...")
connection = obd.OBD("/dev/rfcomm0")  # connect to the adapter

if connection.is_connected():
    print("Connected!")

    cmds = [
        obd.commands.RPM,
        obd.commands.SPEED,
        obd.commands.COOLANT_TEMP
    ]

    while True:
        for cmd in cmds:
            response = connection.query(cmd)
            print(f"{cmd.name}: {response.value}")
        print("-" * 30)
        time.sleep(2)
else:
    print("Failed to connect to OBD-II adapter. Check connection.")
