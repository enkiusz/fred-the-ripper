#
## Robot physics calibration information
#
# Note: These are not possible to automatically detect,
# the robot software just needs to obey those.

#
# Robot arm parameters
#

# Pump catch/release timers [s]
#
# This time is needed to achieve proper pressure with the vacuum system
t_grab = 2
# This time is needed for outside and vacuum system pressures to equalize
# after the pump is off.
t_release = 3

#
# Tray positions
#

# The position of the source tray in arm XYZ coordinates
src_tray_pos = (-99, 79, 100) # [mm]
# This Z value is used for pickup code to prevent the arm from unpopping from the base
src_tray_z_min = 20 # [mm]

# The position of the drive tray in arm XYZ coordinates
drive_tray_pos = (27, 185, 53) # [mm]
# This Z value is used for pickup code to prevent the arm from unpopping from the base
drive_tray_z_min = 1

# The position of the "done" tray in arm XYZ coordinates
done_tray_pos = (-259, 211, 100) # [mm]

# The position of the "error" tray in arm XYZ coordinates
error_tray_pos = (150,300,53) # [mm]


#
# Camera calibration parameters
#
import cv2
import cv2.aruco as aruco

# The ARuCO dictionary identifier used to generate all of the markers
aruco_dict = aruco.DICT_6X6_250

# The marker that is placed on the edge of the CD drive tray
edge_marker_id = 2
edge_marker_filename = 'marker_edge.png'

# The markers that is placed in the middle of the CD in the drive tray
center_marker_id = 5
center_marker_filename = 'marker_center.png'

# The size in pixels of generated marker image files. The markers are square
marker_image_size = 700 # [px]

# The size of the marker in mm. The markers are square.
# This can be used to calculate the distance of the camera to the markers.
marker_size = 20 # [mm]

# This fix is needed because the edge marker is not perfectly aligned with the
# edge of the CD tray. The value is in pixels.
# This marker_size value should ideally be used to calculate the distance to
# the camera which can be used to scale this value.
mask_r_fix = -230 # [px]


#
# Disc presence sensors
#
# The robot uses a TCRT1000 reflective IR sensor in the source tray to detect
# if a disc is present there.
# The sensor is connected to the arm board and interfaced using P241 and M240 commands.
#
# In order to remove the influence of outside light on the IR sensor reading two measurements
# are taken spread by 'sensor_delay' seconds apart. One measurement is taken with the sensor
# builtin IR LED switched on and the other one without it. Then a difference is taken as the
# measurement result.

# LED is switched on/off using D9
led_drive_pin = 9
# Sensor voltage is measured from A3
sensor_voltage_pin = 3

# The amount of time between taking 
sensor_delay = 0.3

# The ADC reading threshold for disc presence detect. When the value
# measured by the ADC on pin 'sensor_voltage' is greater than the threshold
# the robot assumes that a disc is present in the tray
detect_threshold = 200


#
# CD disc information
#

# A CD disc diameter is 120 mm, the internal hole diameter is 15 mm, using this we can
# calculate the radius of the internal hole from the CD radius from the calibration data.
mask_hole_ratio = 0.125

#
## Robot process configuration parameters
#

# The Z-axis step which is used in object grabbing operations
grab_step = 1

close_tray_max_attempts = 3

# The amount of time to wait for the adjustment when camera misalignment
# or bad lighing conditions are detected
camera_calibration_delay = 3

# The amount of time in seconds between attempts at drive selfcheck
selfcheck_drive_action_timeout = 5

# The serial port read timeout
serial_port_timeout = 30

# The amount of time in seconds for looping through the available serial ports
serial_search_delay = 10

# The amount of time in seconds for looping between storage 
storage_search_delay = 10
