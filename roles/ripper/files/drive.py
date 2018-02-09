#!/usr/bin/env python3

import subprocess
import logging

class Drive:
    def __init__(self, device="/dev/cdrom", capture_basedir="."):
        self.log = logging.getLogger(__name__)
        self.device = device
        self.capture_basedir = capture_basedir

    def open_tray(self):
        # Open tray
        returncode = subprocess.call(["eject", self.device])

        if returncode == 0:
            self.log.info("Opened drive tray")
            return True
        else:
            self.log.error("Could not open drive tray")
            return False

    def close_tray(self):
        # Open tray
        returncode = subprocess.call(["eject", "-t", self.device])

        if returncode == 0:
            self.log.info("Closed drive tray")
            return True
        else:
            self.log.warn("Could not close drive tray")
            return False

    def read_disc(self, capture_id):
        # Make the image
        returncode = subprocess.call(["plastic-archiver.sh", "-o", self.capture_basedir, "-i", capture_id, self.device])

        if returncode == 0:
            self.log.info("Successfuly imaged disk")
            return True
        else:
            self.log.warn("Could not image disk")
            return False
