#!/usr/bin/env python3

import logging
import cv2
import os
import numpy as np
import math
import cv2.aruco as aruco
import tempfile
import subprocess

def dist(a,b):
    return math.sqrt( (a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) )

class Vision:
    def __init__(self, config):
        self.config = config
        self.aruco_dict = aruco.Dictionary_get(self.config.aruco_dict)
        self.parameters = aruco.DetectorParameters_create()
        self.log = logging.getLogger(__name__)

    def image_acquire(self, filename=tempfile.mktemp()):

        filename = os.path.realpath(filename)
        returncode = subprocess.call(["shoot-photo.sh", filename])

        if returncode == 0:
            # The chdkptp.sh tool adds the .jpg extension
            filename += ".jpg"

            self.log.info("Acquired image to '{}'".format(filename))
            return filename
        else:
            self.log.warn("Could not acquire image to file '{}'".format(filename))
            return None

    def detect_markers(self, image_filename):
        self.log.info("Searching for markers in '{}'".format(image_filename))

        frame = cv2.imread(image_filename)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        #lists of ids and the corners beloning to each id
        markers, ids, rejectedImgPoints = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.parameters)
        if markers is None or ids is None:
            self.log.warn("Could not detect any markers, make sure that the camera is setup in a correct way")
            return (None, frame)

        if len(markers) != len(ids):
            self.log.fatal("Number of detected markers '{}' is not equal to the number of marker IDs '{}'".format(len(markers), len(ids)))

        self.log.debug(markers)
        self.log.debug(ids)
        self.log.debug(rejectedImgPoints)

        interesting_markers = dict()

        for i in range(len(markers)):
            marker_corners = markers[i][0]
            marker_id = ids[i][0]
            marker_name = None

            xsum = ysum = 0
            for corner in marker_corners:
                xsum = xsum + int(corner[0])
                ysum = ysum + int(corner[1])
                if self.log.isEnabledFor(logging.DEBUG):
                    self.log.debug("Marker ID '{}' Corner = '{}'".format(marker_id, corner))
                    cv2.circle(frame, (corner[0], corner[1]), 20, (0,255,0), -1)

                marker_center = (xsum//4, ysum//4)
                if self.log.isEnabledFor(logging.DEBUG):
                    cv2.circle(frame, marker_center, 20, (255,255,255), -1)

            if marker_id == self.config.center_marker_id:
                marker_name = "disk_center"
            elif marker_id == self.config.edge_marker_id:
                marker_name = "disk_edge"
            else:
                pass

            if marker_name:
                interesting_markers[marker_name] = marker_center

            if self.log.isEnabledFor(logging.DEBUG):
                for rejected_marker in rejectedImgPoints:
                    for corner in rejected_marker[0]:
                        cv2.circle(frame, (corner[0], corner[1]), 5, (255,0,0), -1)


            if self.log.isEnabledFor(logging.DEBUG):
                frame = aruco.drawDetectedMarkers(frame, markers, ids)

        return (interesting_markers, frame)

    def write_cover_image(self, image_filename, cover_filename, calibration_markers):

        self.log.debug("Using calibration data: {}".format(calibration_markers))

        img = cv2.imread(image_filename, cv2.IMREAD_UNCHANGED)

        height = img.shape[0]
        width = img.shape[1]

        self.log.info("Loaded image from file '{}' (resolution {}x{}, {} channels)".format(image_filename, width, height, img.shape[2]) )

        if img.shape[2] != 4:
            self.log.warn("File '{}' doesn't have an alhpa channel, adding".format(image_filename))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)

        disk_center = tuple(calibration_markers['disk_center'])
        disk_edge = tuple(calibration_markers['disk_edge'])
        mask_r = int(math.sqrt( (disk_center[0]-disk_edge[0])**2 + (disk_center[1]-disk_edge[1])**2 )) + self.config.mask_r_fix

        p = disk_center
        r = mask_r

        hole_r = int(r * self.config.mask_hole_ratio)
        self.log.info("Calculated from calibration data: radius {}px, hole radius {}px".format(r, hole_r))

        if self.log.isEnabledFor(logging.DEBUG):
            cv2.circle(img, disk_center, 5, (255.0,0), -1)
            cv2.circle(img, disk_edge, 5, (255.0,0), -1)

        edges = cv2.Canny(cv2.medianBlur(img, 5), 100, 200)
        if self.log.isEnabledFor(logging.DEBUG):
            cv2.imwrite('src-image-edges.jpg', edges)

        circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, 1, 20, param1=50, param2=30, minRadius=np.uint16(r*0.98), maxRadius=np.uint16(r*1.02))

        if circles is not None:

            circles = np.uint16(np.around(circles))
            self.log.info("Found {} circles on image".format(len(circles[0,:])))

            min_d = 1000

            for i in circles[0,:]:

                if self.log.isEnabledFor(logging.DEBUG):
                    cv2.circle(img, (i[0], i[1]), i[2], (255,255,255), 2)

                dp = dist(disk_center, (i[0], i[1]))
                dr = abs(i[2] - mask_r)
                # self.log.debug("Circle pos {} r={}, dp={} dr={}, d={}".format((i[0], i[1]), i[2], dp, dr, dp + dr))

                if  dp + dr < min_d:
                    p = (i[0], i[1])
                    r = i[2]
                    min_d = dp + dr

            self.log.info("Best circle p=%s r=%s" % (p, r))


        else:
            self.log.warn("No circles detected on image, using calibration data directly")

        if self.log.isEnabledFor(logging.DEBUG):
            # Draw the mask circle
            cv2.circle(img, p, r, (255,255,255),5)

            # draw the circle centers
            cv2.circle(img, p, r,(0,255,0),10)
            cv2.circle(img, p, 5, (0.255,0), -1)

            cv2.imwrite("src-image-debug.jpg", img)

        mask_img = np.zeros((height, width, 4), np.uint8)

        cv2.circle(mask_img, p, r, (255,255,255,255), -1)
        cv2.circle(mask_img, p, hole_r, (0,0,0,0), -1)

        if self.log.isEnabledFor(logging.DEBUG):
            cv2.imwrite("mask.png", mask_img)

        cd = cv2.bitwise_and(img, mask_img)

        if self.log.isEnabledFor(logging.DEBUG):
            cv2.imwrite("image-masked.png", cd)

        cd = cd[p[1] - r:p[1] + r, p[0] - r:p[0] + r]

        cv2.imwrite(cover_filename, cd)

def main():

    import config
    import time
    import logging
    from drive import Drive

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)

    log.info("Testing vision subsystem")

    vision = Vision(config)
    drive = Drive()
    drive.close_tray()

    calibration_markers = None
    while True:

        drive.close_tray()

        log.info("Acquiring calibration image")
        image_filename = vision.image_acquire()
        if not image_filename:
            log.warn("Could not acquire image for calibration, please check the camera")
            time.sleep(config.camera_calibration_delay)
            continue

        (calibration_markers,frame) = vision.detect_markers(image_filename)
        os.unlink(image_filename)

        log.debug("Markers detected during calibration: '{}'".format(calibration_markers))

        if calibration_markers and 'disk_center' in calibration_markers and 'disk_edge' in calibration_markers:
            break
        else:
            log.warn("Both calibration markers need to be detectable, please adjust the camera or lighting conditions")
            time.sleep(config.camera_calibration_delay)

    log.info("Camera calibration was successful, calibration markers detected: {}".format(calibration_markers))

    drive.open_tray()

    camera_image_filename = vision.image_acquire('camera-image')
    vision.write_cover_image(camera_image_filename, 'cover.png', calibration_markers)

    drive.close_tray()

if __name__ == "__main__":
    main()

