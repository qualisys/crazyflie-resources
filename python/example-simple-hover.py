# -*- coding: utf-8 -*-

""" Example script for hovering Crazyflie at a static position and listening to QTM events.

A new (blank) measurement must be open in QTM before the script is run!
Do not stop QTM measurement before stopping the script!

To positions are defined - a "home" position and an "away" position.
Crazyflie lifts and hovers at the "home" position when the script is started.
Triggering an event in QTM (while recording) toggles between positions.
"""

import math
import os
import time

import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
import qtm
from twisted.internet import threads
import xmltodict

from helpers import convert_coords_to_setpoint, crazyflie_reset_estimator, print_status

# Settings
CRAZYFLIE_URI = "radio://0/80/2M"
QTM_IP = "127.0.0.1"
CRAZYFLIE_RIGIDBODY_NAME = "Crazyflie"
FRAME_LOSS_THRESHOLD = 3
HOME_POSITION = (0.0, 0.0, 0.3, 0.0)  # (X, Y, Z, Yaw)
AWAY_POSITION = (0.1, 0.1, 0.5, 0.0)  # (X, Y, Z, Yaw)

# Initializing
scf = None
qtmRigidbodies_idxByName = {}
trackingFramesLost = 0
target = HOME_POSITION
flyAway = False


def on_qtm_connect(connection, version):
    """Callback to handle QTM connection"""

    print('Connected to QTM, version {}'.format(version.decode("UTF-8")))

    print("Getting parameters from QTM...")
    connection.get_parameters(on_ok=qtm_receive_params)

    print("Starting to record new measurement in QTM...")
    connection.start(on_ok=lambda result: print("QTM capture started -", result.decode("utf-8")),
                     on_error=lambda result: print("Error starting QTM capture!", result.decode("utf-8")))

    print("Starting listening to QTM packet stream...")
    connection.stream_frames(frames='allframes', components=['6deuler'], on_packet=on_qtm_packet)


def qtm_receive_params(params):
    """Callback to handle incoming parameters from QTM"""

    global qtmRigidbodies_idxByName

    try:
        params = xmltodict.parse(params.decode("utf-8"))
        bodies_info = params['QTM_Parameters_Ver_1.17']['The_6D']
        print("Found {} 6DoF bodies defined in QTM project:".format(bodies_info['Bodies']))
        bodies = bodies_info['Body']
        for i, body in enumerate(bodies):
            print("\t({}) {}".format(i, body['Name']))
            qtmRigidbodies_idxByName[body['Name']] = i
    except Exception as e:
        print("Terminating due to error receiving QTM parameters:", str(e))
        os._exit(1)


def on_qtm_disconnect(reason):
    """Callback to handle QTM disconnect"""
    print("Terminating due to QTM disconnect, reason:", reason)
    os._exit(1)


def on_qtm_event(event):
    """Callback to handle QTM events
    Trigger events toggle target between home/away positions
    CaptureStopped events terminate the program
    """

    global flyAway, target, AWAY_POSITION, HOME_POSITION

    print("QTM Event received:", event)

    if event == qtm.QRTEvent.EventTrigger:
        print("Trigger event received - toggling position...")
        flyAway = not flyAway

        if flyAway:
            target = AWAY_POSITION
        else:
            target = HOME_POSITION
    elif event in (qtm.QRTEvent.EventCaptureStopped, qtm.QRTEvent.EventCameraSettingsChanged):
        print("CaptureStopped or CameraSettingsChanged event received - terminating.")
        os._exit()


def on_qtm_packet(packet):
    """Callback to handle QTM packets"""

    global scf, CRAZYFLIE_RIGIDBODY_NAME, qtmRigidbodies_idxByName, trackingFramesLost

    # Get rigidbody data from QTM
    header, bodies = packet.get_6d_euler()

    # Increment frame loss counter if anything is wrong
    if not scf or not bodies:
        trackingFramesLost += 1
        return

    # Get position for Crazyflie
    crazyflie_rigidbody = bodies[qtmRigidbodies_idxByName[CRAZYFLIE_RIGIDBODY_NAME]]

    # The positions returned by QTM is in 'mm' - divide by 1000 to convert to 'm'
    cf_pos = [coord / 1000.0 for coord in crazyflie_rigidbody[0]]

    # print("Crazyflie position: {}".format(cf_pos))

    # If QTM loses tracking it may return `NaN` which can crash Crazyflie if sent
    # In case of `Nan` values, don't send to Crazyflie, and increment frame loss counter
    if any([math.isnan(coord) for coord in cf_pos]):
        trackingFramesLost += 1
    else:
        scf.cf.extpos.send_extpos(*cf_pos)
        trackingFramesLost = 0


def crazyflie_controller():
    """Crazyflie flight controller - initializes position estimator and calls for flight instructions"""

    global scf, CRAZYFLIE_URI, flyAway

    # Reset target before liftoff for safety
    flyAway = False

    try:
        with SyncCrazyflie(CRAZYFLIE_URI) as _scf:
            # Update global Synchronous Crazyflie object when connected
            scf = _scf
            if not scf:
                print("Crazyflie is not True! Terminating.")
                os._exit(1)
            else:
                print("Connected to Crazyflie at", CRAZYFLIE_URI, "- resetting position estimator...")
                crazyflie_reset_estimator(scf)
                crazyflie_fly()
    except Exception as e:
        print("Terminating due to error while initializing flight controller:", str(e))
        os._exit(1)


def crazyflie_fly():
    """Provides flight instructions to Crazyflie based on global `fly` variable"""

    global scf, target, FRAME_LOSS_THRESHOLD, trackingFramesLost

    cf = scf.cf
    cf.param.set_value('flightmode.posSet', '1')

    # Crazyflie needs to be sent a setpoint at least twice a second or it will stop
    while True:
        time.sleep(0.1)
        # Check if tracking is good
        if trackingFramesLost <= FRAME_LOSS_THRESHOLD:
            print_status("Setting position {}".format(target))
            setpoint = convert_coords_to_setpoint(target)
            cf.commander.send_setpoint(*setpoint)
        else:
            cf.commander.send_stop_setpoint()
            print("Tracking lost, terminating.")
            os._exit(1)


if __name__ == '__main__':
    print("~ Qualisys x CrazyFlie ~")

    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Connect to QTM on a specific ip
    qrt = qtm.QRT(QTM_IP, 22223, version='1.17')
    qrt.connect(on_connect=on_qtm_connect, on_disconnect=on_qtm_disconnect, on_event=on_qtm_event)

    # Start Crazyflie flight controller on a new thread
    threads.deferToThread(crazyflie_controller)

    # Start running the processes
    qtm.start()
