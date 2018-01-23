# -*- coding: utf-8 -*-

"""Helper functions for QTM x Crazyflie integration examples.
"""

import time

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

lastStatusMessage = ""


def convert_coords_to_setpoint(coords):
    """Converts the more readable (X, Y, Z, Yaw) coordinates to Crazyflie (Y, X, Yaw, Thrust) setpoints"""
    # Thrust is calculated by multiplying Z by 1000
    return coords[1], coords[0], coords[3], int(coords[2] * 1000)


def crazyflie_reset_estimator(scf):
    """Resets the Crazyflie position estimator."""

    # Reset the Kalman filter
    cf = scf.cf
    cf.param.set_value('kalman.resetEstimation', '1')
    time.sleep(0.1)
    cf.param.set_value('kalman.resetEstimation', '0')
    time.sleep(0.1)

    print('Waiting for estimator to find stable position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("Errors: ({}, {}, {})".format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                print("Position found with errors (x: {}, y: {}, z: {})"
                      .format(max_x - min_x, max_y - min_y, max_z - min_z))
                break


def print_status(message):
    """Prints status messages to console, but only if something new has happened"""

    global lastStatusMessage

    if lastStatusMessage != message:
        print(message)
        lastStatusMessage = message
