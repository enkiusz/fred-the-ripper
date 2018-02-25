#!/usr/bin/env python3

import subprocess
import logging
import re
import psutil
import os
import pwd

class Storage:
    def __init__(self, config):
        self.log = logging.getLogger(__name__)
        self.path = '/mnt/storage'
        self.config = config

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
        proc = subprocess.run("lsblk -lpn --output LABEL,NAME | grep -F -- {}".format(self.config.storage_fs_label), shell=True, check=True, stdout=subprocess.PIPE)
        self.device = proc.stdout.decode('ascii').rstrip().split()[1]

        if proc.returncode != 0:
            return False
        if not re.match('/dev/sd[a-z][1-9][0-9]?', self.device):
            self.log.error("Unexpected device detected as storage: '{}'".format(proc.stdout))
            return False

        # Check if storage is mounted
        if not self.storage_available():
            # This is for VFAT
            # proc = subprocess.run(['sudo', 'mount', self.device, self.path, '-o', 'uid={},gid={}'.format(os.getuid(), os.getgid())], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # This is for EXT2/3/4 and other filesystems with UNIX-style permissions
            proc = subprocess.run(['sudo', 'mount', self.device, self.path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Change ownership of root storage path so that we can create files there
            os.system("sudo chown {} {}".format(pwd.getpwuid(os.getuid()).pw_name, self.path))

            if proc.returncode == 0:
                return True
            else:
                self.log.error("Could not mount device '{}' into '{}', return code is '{}', output is '{}' stderr is '{}'".format(self.device, self.path, proc.returncode, proc.stdout, proc.stderr))
                return False
        else:
            return True

if __name__ == "__main__":
    import config

    logging.basicConfig(level=logging.DEBUG)

    log = logging.getLogger(__name__)
    storage = Storage(config)

    result = storage.detect()
    log.info("Detection returned {}".format(result))

    if result is True:
        log.info("Storage device is '{}'".format(storage.device))
        log.info("Storage path is '{}'".format(storage.path))
