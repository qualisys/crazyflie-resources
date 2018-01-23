# Resources for Using Bitcraze Crazyflie Drones with Qualisys Systems

[Qualisys motion capture systems](http://www.qualisys.com/) can provide high-speed, reliable, precision position tracking for the closed-loop control of [Bitcraze](https://www.bitcraze.io/) [Crazyflie](https://www.bitcraze.io/crazyflie-2/) quadcopter systems. This repository contains a collection of resources for developing Crazyflie projects and related applications that interact with QTM.

![](https://s3-eu-west-1.amazonaws.com/content.qualisys.com/2016/12/drone-Ericsson.jpg)

## Python Script Examples

The Python scripts in the "python" folder in this repository are intended to serve as a starting point for implementing custom Crazyflie applications.

### Requirements and Setup Instructions

All scripts have been tested with Python 3.6.4 running on Windows 10 in a [conda](https://conda.io/) environment.

Required packages:

- [cflib](https://pypi.python.org/pypi/cflib)
- [qtm](https://pypi.python.org/pypi/qtm/)
- [xmltodict](https://pypi.python.org/pypi/xmltodict)

### Caveats

Albeit small and lightweight, the Crazyflie drone may damage itself, along with objects and people in its vicinity upon contact. Please be mindful of the surroundings and remember that a motion capture / position tracking system does not necessarily provide facilities for collision avoidance.

Additionally, while controlling Crazyflie drones programmatically using a Qualisys motion capture system, please be aware of the following issues:

- Running the control loop that issues `send_setpoint()` commands to the Crazyflie while no position information is relayed (via `send_extpos()`) may cause the drone to **fly uncontrollably and crash**. The control loop that issues commands to the Crazyflie **must be stopped before stopping streaming from QTM**. 
