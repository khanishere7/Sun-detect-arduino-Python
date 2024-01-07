import numpy as np
import cv2
import urllib.request
from time import sleep
from pyfirmata import SERVO, Arduino

url = "http://192.168.1.15/cam-hi.jpg"
video_capture = cv2.VideoCapture(url)
radius = 41  # must be an odd number, or else GaussianBlur will fail
circleColor = (0, 0, 255)
circleThickness = 15
font = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 1
fontColor = (255, 255, 255)
fontThickness = 2

# Arduino setup for servo control
port = "COM7"  # Adjust the port accordingly
pin = 2  # GPIO 2 on the ESP32
board = Arduino(port, baudrate=115200)
servo = board.get_pin(f"d:{pin}:s")  # Servo object

# Function to calculate distance between two points
def calculate_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

# Function to calculate angle based on vertical position
def calculate_angle_vertical(position_y, image_height):
    max_angle = 90  # Maximum angle for the servo rotation
    angle = max_angle * (position_y / image_height)
    return angle

def move_servo_to_center(maxLoc, center, image_height):
    angle = calculate_angle_vertical(maxLoc[1], image_height)
    servo.write(angle)
    sleep(0.1)  # Adjust the delay as needed

while video_capture.isOpened():
    try:
        img_resp = urllib.request.urlopen(url, timeout=10)
        imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        frame = cv2.imdecode(imgnp, -1)

        if frame is None:
            print("Error: Frame not retrieved from video capture.")
            break

        image = frame.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # perform a naive attempt to find the (x, y) coordinates of
        # the area of the image with the largest intensity value
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(gray)
        cv2.circle(image, maxLoc, 5, circleColor, circleThickness)

        # calculate distance between the detected spot and the center of the image
        center = (image.shape[1] // 2, image.shape[0] // 2)
        distance_to_center = calculate_distance(maxLoc, center)

        # move the servo to center the brightest spot
        move_servo_to_center(maxLoc, center, image.shape[0])

        # display the results of the naive attempt
        cv2.putText(image, "Naive", (10, 30), font, fontScale, fontColor, fontThickness, cv2.LINE_AA)
        cv2.imshow("Naive", image)

        # apply a Gaussian blur to the image then find the brightest region
        gray = cv2.GaussianBlur(gray, (radius, radius), 0)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(gray)
        image = frame.copy()  # Ensure that we are copying the original frame

        cv2.circle(image, maxLoc, radius, circleColor, circleThickness)

        # move the servo to center the brightest spot
        move_servo_to_center(maxLoc, center, image.shape[0])

        # display the results of our newly improved method
        cv2.putText(image, "Robust", (10, 30), font, fontScale, fontColor, fontThickness, cv2.LINE_AA)
        cv2.circle(image, maxLoc, radius, circleColor, circleThickness)

        # check if the brightest spot is close to the center
        threshold_distance = 300  # Adjust this threshold as needed
        if distance_to_center < threshold_distance:
            result_text = "Brightest spot is at the center!"
        else:
            result_text = "Brightest spot is not at the center."

        # display the result text on the video window
        cv2.putText(image, result_text, (10, 70), font, fontScale, fontColor, fontThickness, cv2.LINE_AA)

        cv2.imshow("Robust", image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    except Exception as e:
        print(f"Error: {e}")
        break

# Release the VideoCapture, release the servo, and close all windows
video_capture.release()
board.exit()
cv2.destroyAllWindows()
