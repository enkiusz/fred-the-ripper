#!/usr/bin/env python3

import logging
import os

class Display:
    def __init__(self, config):
        self.config = config
        self.display_dir = "/run/fred"

    def msg(self, msg):
        with open(os.path.join(self.display_dir, 'line1'), "w") as f:
            f.write("{}\n".format(msg))

def main():

    import config
    import logging
    import time

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)

    log.info("Testing display subsystem")

    display = Display(config)

    i = 0

    while True:
        display.msg("c={}".format(i))

        i += 1
        time.sleep(1)

if __name__ == "__main__":
    main()
