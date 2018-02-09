#!/usr/bin/env python3

import subprocess
import logging
import re
import psutil

class Storage:
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.path = '/mnt/storage'

    def storage_available(self):
        parts = [part for part in psutil.disk_partitions() if part.mountpoint == self.path and part.device == self.device]
        if len(parts) == 1:
            return True
        elif len(parts) == 0:
            return False
        else:
            log.warn("Unexpected list of partitions when looking for storage state: '{}'".format(psutil.disk_partitions()))
            return None

    def detect(self):
        proc = subprocess.run("lsblk --json --output NAME,RM,RO,TYPE,FSTYPE | jq -r '.blockdevices | map(select(.rm == \"1\" and .type == \"disk\")) | first | .children | map(select(.fstype != \"iso9660\")) | first | .name'", shell=True, check=True, stdout=subprocess.PIPE)
        dev = proc.stdout.decode('ascii').rstrip()

        if proc.returncode != 0:
            return False
        if not re.match('sd[a-z][1-9][0-9]?', dev):
            log.error("Unexpected device detected as storage: '{}'".format(proc.stdout))
            return False

        self.device = '/dev/{}'.format(dev)

        # Check if storage is mounted
        if not self.storage_available():
            proc = subprocess.run(['sudo', 'mount', self.device, self.path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if proc.returncode == 0:
                return True
            else:
                log.error("Could not mount device '{}' into '{}', return code is '{}', output is '{}' stderr is '{}'".format(self.device, self.path, proc.returncode, proc.stdout, proc.stderr))
                return False
        else:
            return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    log = logging.getLogger(__name__)
    storage = Storage()

    result = storage.detect()
    log.info("Detection returned {}".format(result))

    if result is True:
        log.info("Storage device is '{}'".format(storage.device))
        log.info("Storage path is '{}'".format(storage.path))
