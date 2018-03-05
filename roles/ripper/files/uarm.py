#!/usr/bin/env python3

import logging
import re
import time

class UArm:
    default_speed = 100
    READY = '@1'

    def __init__(self, serial, config):
        self.comm = serial
        self.config = config
        self.log = logging.getLogger(__name__)

        self.cmd_id = 1
        self.max_running_cmds = 100
        #
        # Robot configuration
        #
        # Delay for 200 ms between queries
        self.move_wait_query_delay = 0.2
        # Time out after 60 seconds
        self.move_wait_max_tries = int(60 / self.move_wait_query_delay)

    def connect(self):
        if self.wait_for_ready():
            self.probe()
            self.origin()
            return True
        else:
            self.log.fatal("Uarm is not ready")
        return False

    def exec_cmd(self, cmd):
        cmdstring = '#{} {}'.format(self.cmd_id, cmd)
        self.log.debug("Executing command '{}'".format(cmdstring))

        self.cmd_id = (self.cmd_id + 1) % self.max_running_cmds

        cmdstring = cmdstring + "\n"
        self.comm.write(cmdstring.encode('ascii'))
        resp = self.comm.readline().decode('ascii').rstrip()
        self.log.debug("Received response '{}'".format(resp))
        return resp

    # Wait for the Uarm to send a "READY" token
    def wait_for_ready(self):
        resp = self.comm.readline().decode('ascii').rstrip()
        if resp == '@1':
            return True
        else:
            self.log.error("Uarm would not signal READY, instead got '{}'".format(resp))
            return False

    def probe(self):

        self.device_name = self.exec_cmd("P201").split(' ')[2]
        self.hw_version = self.exec_cmd("P202").split(' ')[2]
        self.sw_version = self.exec_cmd("P203").split(' ')[2]
        self.api_version = self.exec_cmd("P204").split(' ')[2]
        self.uid = self.exec_cmd("P205").split(' ')[2]
        self.log.info("Detected device '{}' HW v'{}' SW v'{}' API v'{}' UID='{}'". format(
            self.device_name, self.hw_version, self.sw_version, self.api_version,
            self.uid
        ))

    def origin(self):
        # Set initial position, the same as UFactory uClient v 2.0
        #1 M231 V0
        #1 M232 V0
        #1 G0 X0 Y150 Z100 F0
        #1 G202 N3 V90.0
        #1 G0 X0 Y150 Z100 F0
        self.pump(False)
        self.grip(False)
        self.move_abs((0, 150, 100), 0)
        self.servo_abs(3, 90)
        self.move_abs((0, 150, 100), 0)

    def robot_moving(self):
        resp = self.exec_cmd("M200")
        move_state = resp.split(' ')[2]
        if move_state == "V1":
            return True
        elif move_state == "V0":
            return False
        else:
            self.log.error("Unknown response for move check command: '{}'".format(resp))
            return '?'

    def wait_for_move_end(self):
        for i in range(self.move_wait_max_tries):
            if not self.robot_moving():
                return
            time.sleep(self.move_wait_query_delay)
        self.log.error("Timeout '{}' seconds while waiting for robot to stop moving".format(self.move_wait_max_tries * self.move_wait_query_delay))

    def servo_abs(self, servo_id, angle):
        return self.exec_cmd("G202 N{} V{}".format(servo_id, angle))

    def move_abs(self, p, speed=default_speed):
        return self.exec_cmd("G0 X{} Y{} Z{} F{}".format(p[0],p[1],p[2],speed))

    def move_rel(self, dp, speed=default_speed):
        return self.exec_cmd("G204 X{} Y{} Z{} F{}".format(dp[0],dp[1],dp[2],speed))

    def analogread(self, pin):
        m = re.search("OK V([-.0-9]+)", self.exec_cmd("P241 N{}".format(pin)) )
        if m:
            return float(m.group(1))
        else:
            return None

    def digitalout(self, pin, state):
        if state:
            v = 1
        else:
            v = 0
        return self.exec_cmd("M240 N{} V{}".format(pin, v))

    def pos(self):
        m = re.search("OK X([-.0-9]+) Y([-.0-9]+) Z([-.0-9]+)", self.exec_cmd("P220") )
        if m:
            return ( float(m.group(1)), float(m.group(2)), float(m.group(3)) )
        else:
            return None

    def pump(self, state):
        if state:
            v = 1
        else:
            v = 0
        return self.exec_cmd("M231 V{}".format(v))

    def grip(self, state):
        if state:
            v = 1
        else:
            v = 0
        return self.exec_cmd("M232 V{}".format(v))

    def switch_state(self):
        resp = self.exec_cmd("P233")
        sw_state = resp.split(' ')[2]
        if sw_state == "V1":
            return True
        elif sw_state == "V0":
            return False
        else:
            self.log.error("Unknown response for switch state command: '{}'".format(resp))
            return '?'

    def pickup_object(self, p, z_min):
        limit_switch = False
        self.move_abs(p)
        self.wait_for_move_end()

        while p[2] > z_min:
            p = (p[0], p[1], p[2] - self.config.grab_step)
            self.move_abs(p)
            self.wait_for_move_end()

            if not self.switch_state():
                limit_switch = True
                return True

        if not limit_switch:
            self.log.error("Reached z min '{}' but item was not detected".format(z_min))
            return False

        self.log.fatal("An unforseen state has been detected, reached position '{}' with z_min '{}' and switch state '{}'".format(pz, z_min, limit_switch))
        return None

def main():

    import config
    import logging
    import serial
    import time
    import sys

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)

    log.info("Testing arm subsystem")

    uarm_device = sys.argv[1]

    serial_port = serial.Serial(port=uarm_device, baudrate=115200, timeout=config.serial_port_timeout)
    arm = UArm(serial_port, config)
    if arm.connect():
        log.info("Detected UArm on device {}".format(uarm_device))
    else:
        log.fatal("Could not connect to uArm on device {}".format(uarm_device))

    #
    # Wait for a disc to be detected in the source tray
    #
    while True:
        # Switch off LED
        arm.digitalout(config.led_drive_pin, False)
        led_off = arm.analogread(config.sensor_voltage_pin)

        time.sleep(config.sensor_delay)

        # Switch on LED
        arm.digitalout(config.led_drive_pin, True)
        led_on = arm.analogread(config.sensor_voltage_pin)

        signal = led_on - led_off

        log.debug("A{} readout led on D{} off '{}' led on '{}' signal '{}'".format(config.sensor_voltage_pin, config.led_drive_pin,
                                                                                   led_off, led_on, signal))

        if signal > config.detect_threshold:
            log.info("Disc detected in source tray (signal value is '{}')".format(signal))
            break

        time.sleep(config.sensor_delay)

if __name__ == "__main__":
    main()
