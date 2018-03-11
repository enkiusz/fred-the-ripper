#!/usr/bin/env python3

import serial
import sys
import time
import logging
import os
import json
import argparse
from uarm import UArm
from vision import Vision
from drive import Drive
from storage import Storage
from display import Display

import config

parser = argparse.ArgumentParser()
parser.add_argument("--arm-device", dest='device', help="UArm serial port device")
parser.add_argument("--capture-id", dest="capture_id", help="Capture ID")
parser.add_argument("--storage-path", dest="storage_path", help="Storage root path")
parser.add_argument("--calibration-markers", dest="calibration_markers_file", help="Calibration marker positions")

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
rootlog = logging.getLogger(None)

display = Display(config)

arm = UArm(serial.Serial(port=args.device, baudrate=115200, timeout=config.serial_port_timeout), config)
if arm.connect():
    log.info("Detected UArm on device {}".format(args.device))
else:
    log.fatal("Could not connect to UArm using device '{}'".format(args.device))

storage_path = args.storage_path
capture_id = args.capture_id

log.info("Using storage '{}'".format(storage_path))

vision = Vision(config)

drive = Drive("/dev/cdrom", storage_path)

calibration_markers = None
with open(args.calibration_markers_file, 'r') as f:
    calibration_markers = json.load(f)

log.info("Calibration data loaded from '{}': {}".format(args.calibration_markers_file, calibration_markers))

log.info("Starting capture")

log.info("Picking up disk from source tray")
display.msg("PICKUP SRC TRAY")

# Pickup disk
cd_pickedup = arm.pickup_object(config.src_tray_pos, config.src_tray_z_min)
if not cd_pickedup:
    log.fatal("Could not pick up disk, bailing out")
    display.msg("ERR PICKUP DISK")
    sys.exit(1)

arm.pump(True)
time.sleep(config.t_grab)

display.msg("MOVE TO DRIVE")

arm.move_abs(config.src_tray_pos)
arm.wait_for_move_end()

drive.open_tray()

arm.move_abs(config.drive_tray_pos)
arm.wait_for_move_end()

arm.pump(False)
time.sleep(config.t_release)

arm.origin()

for i in range(config.close_tray_max_attempts):
    if drive.close_tray():
        break

    log.warn("Could not close drive tray, retry '{}' of '{}'".format(i, config.close_tray_max_attempts))
    display.msg("ERR DRIVE CLOSE")
    drive.open_tray()

# Move the arm away so that the camera can make a photo of the disc
arm.move_abs(config.src_tray_pos)

log.info("Archiving disc in drive tray")
display.msg("IMAGING ...")

dest_tray = config.done_tray_pos

if not drive.read_disc(capture_id):
    log.error("Disk could not be imaged, putting into FAILED tray")
    display.msg("IMAGING FAIL")
    dest_tray = config.error_tray_pos
else:
    log.info("Disc successfuly imaged, putting to DONE tray")

drive.open_tray()

try:
    tmp_image_filename = vision.image_acquire()
    vision.write_cover_image(tmp_image_filename, '{}/{}/cover.png'.format(storage_path, capture_id), calibration_markers)
except:
    log.error("Could not acquire image and write a cover file")
    display.msg("ERR ACQ. COVER IMG")
    dest_tray = config.error_tray_pos
finally:
    if tmp_image_filename:
        os.unlink(tmp_image_filename)

cd_pickedup = arm.pickup_object(config.drive_tray_pos, config.drive_tray_z_min)
if not cd_pickedup:
    log.fatal("Could not pick up CD, bailing out")
    display.msg("ERR DISK PICKUP")
    sys.exit(1)

arm.pump(True)
time.sleep(config.t_grab)

display.msg("MOVE TO DST TRAY")

arm.move_abs(config.drive_tray_pos)
arm.wait_for_move_end()

arm.move_abs(dest_tray)
arm.wait_for_move_end()

arm.pump(False)
time.sleep(config.t_release)

drive.close_tray()

arm.origin()

