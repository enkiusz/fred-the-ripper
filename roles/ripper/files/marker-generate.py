#!/usr/bin/python3

import config
import cv2
import cv2.aruco as aruco

aruco_dict = aruco.Dictionary_get(config.aruco_dict)

cv2.imwrite(config.center_marker_filename, aruco.drawMarker(aruco_dict, config.center_marker_id, config.marker_image_size))
cv2.imwrite(config.edge_marker_filename, aruco.drawMarker(aruco_dict, config.edge_marker_id, config.marker_image_size))

