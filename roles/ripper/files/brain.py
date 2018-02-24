#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import sys
import time
import logging
import os
import subprocess
import uuid
import json
from uarm import UArm
from vision import Vision
from drive import Drive
from storage import Storage
from display import Display

import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

display = Display(config)

arm_device = None
serial_port = None
arm = None

display.msg("DETECT ARM")
log.info("Detecting where the robot arm is connected")

while True:

    for s in serial.tools.list_ports.comports():

        log.debug("Probing for UArm on serial port '{}' ({})".format(s.device, s.hwid))

        serial_port = serial.Serial(port=s.device, baudrate=115200, timeout=config.serial_port_timeout)
        arm = UArm(serial_port, config)
        if arm.connect():
            arm_device = s.device
            log.info("Detected UArm on device {}".format(s.device))
            display.msg("ARM OK")

    if arm is not None:
        break

    log.info("No UArm detected on any of the serial ports, retrying in {} seconds".format(config.serial_search_delay))
    display.msg("NO ARM, RETRY IN {} SECONDS".format(config.serial_search_delay))
    time.sleep(config.serial_search_delay)

log.info("Getting list of storage")
display.msg("DETECT STORAGE")

storage = Storage(config)
while True:
    if storage.detect() is True:
        break

    display.msg("NO STORAGE, RETRY IN {} SECONDS".format(config.storage_search_delay))
    time.sleep(config.storage_search_delay)

storage_path = storage.path

log.info("Detected storage '{}'".format(storage_path))
display.msg("STORAGE OK")

vision = Vision(config)

drive = Drive("/dev/cdrom", storage_path)

# Self-test
log.info("Starting drive self-check")
display.msg("DRIVE SELF-CHECK")

#
# This self-check is needed because the JM20337 SATA<->USB bridge takes a while to realize
# that power is on, the drive is connected and it's time to get to work and announce itself on
# the USB bus.
#
while True:

    # Try to open the drive tray
    if not drive.open_tray():
        log.warn("Could not open drive tray, please check drive")
        display.msg("CANNOT OPEN, RETRY IN {} SECONDS".format(config.selfcheck_drive_action_timeout))
        time.sleep(config.selfcheck_drive_action_timeout)
        continue

    # Try to close the drive tray
    if not drive.close_tray():
        log.warn("Could not close drive tray, please check drive")
        display.msg("CANNOT CLOSE, RETRY IN {} SECONDS".format(config.selfcheck_drive_action_timeout))
        time.sleep(config.selfcheck_drive_action_timeout)
        continue

    log.info("Drive self-check passed")
    display.msg("DRIVE OK")
    break

# Calibrate camera
log.info("Starting camera calibration")
display.msg("CALIBRATE VISION")

calibration_markers = None
while True:

    # Move the arm away so that the camera can make a photo of the markers
    # Also close the tray so that both markers are unobstructed
    arm.move_abs(config.src_tray_pos)
    arm.wait_for_move_end()
    drive.close_tray()

    log.info("Acquiring calibration image")
    display.msg("IMAGE ACQUIRE")

    image_filename = vision.image_acquire()
    if not image_filename:
        log.warn("Could not acquire image for calibration, please check the camera")
        display.msg("CANNOT ACQUIRE IMAGE, RETRY IN {} SECONDS".format(config.camera_calibration_delay))
        time.sleep(config.camera_calibration_delay)
        continue

    (calibration_markers,frame) = vision.detect_markers(image_filename)
    os.unlink(image_filename)

    log.debug("Markers detected during calibration: '{}'".format(calibration_markers))

    if calibration_markers and 'disk_center' in calibration_markers and 'disk_edge' in calibration_markers:
        break
    else:
        log.warn("Both calibration markers need to be detectable, please adjust the camera or lighting conditions")
        display.msg("NO MARKERS, RETRY IN {} SECONDS".format(config.camera_calibration_delay))
        time.sleep(config.camera_calibration_delay)

log.info("Camera calibration was successful, calibration markers detected: {}".format(calibration_markers))
display.msg("VISION OK")

with open(config.calibration_filename, 'w') as f:
    json.dump(calibration_markers, f)

while True:

    log.info("Waiting for a disc to be placed in the source tray")
    display.msg("WAITING FOR DISK IN SOURCE TRAY")

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
            display.msg("DETECTED DISK")
            break

        time.sleep(config.sensor_delay)

    # Close the serial port so that the ripper.py script can open it again
    serial_port.close()

    capture_id = str(uuid.uuid4())

    capture_unit_name = 'ripper@{}.service'.format(capture_id)
    subprocess.call(['sudo', 'systemd-run', '--uid', str(os.getuid()), '--unit', capture_unit_name, '--wait', 'ripper.py', '--arm-device', arm_device, '--capture-id', capture_id, '--storage-path', storage_path, '--calibration-markers', config.calibration_filename])

    # Store the logs
    os.system("journalctl -a --utc -o short-iso _SYSTEMD_UNIT={} > {}/{}/log.txt".format(capture_unit_name, storage_path, capture_id))

    # Reopen the UArm device
    serial_port = serial.Serial(port=arm_device, baudrate=115200, timeout=config.serial_port_timeout)
    arm = UArm(serial_port, config)
    arm.connect()

arm.origin()
s.close()

