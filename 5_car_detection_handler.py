import cv2
import numpy as np
import time
from multi import VideoStreamWidget
import requests
import paho.mqtt.client as mqtt
net = cv2.dnn.readNet('yolov3-tiny_final.weights', 'yolov3-tiny.cfg')

classes = []
with open("yolov3cars.txt", "r") as f:
    classes = f.read().splitlines()


SAFE_THRESHOLD = 1.05
BEWARE_THRESHOLD = 1.10
DANGER_THRESHOLD = 1.38
WIDTH_BOUND = 0.5
MAX_SIZE = 0.35
# WEMOS_IP = "http://192.168.32.45"
EQUATIONS = None

# capture = cv2.VideoCapture('http://192.168.108.34:8080/video')
capture = VideoStreamWidget("http://172.25.96.28:8080/video")
# capture = VideoStreamWidget("./clips/ezgif.com-gif-maker.mov")
# capture = VideoStreamWidget(0)
# capture = VideoStreamWidget("driving.mp4")

# capture = VideoStreamWidget("untitled.mp4")
# W, H = 480, 360
# capture.set(cv2.CAP_PROP_FRAME_WIDTH, W)
# capture.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
# capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
# capture.set(cv2.CAP_PROP_FPS, 30)
# cap = cv2.VideoCapture(0)
time.sleep(0.5)
font = cv2.FONT_HERSHEY_PLAIN
colors = np.random.uniform(0, 255, size=(100, 3))


def equation_finder(point1, point2):
    m = (point2[1] - point1[1]) / (point2[0] - point1[0])
    c = point2[1] - m*point2[0]

    return (m,c)

def road_equation(width, height):
    #ul, ur, bl, br -> four corners
    ul = int(width * 7 / 16) 
    ur = width - ul

    bl = int(width*4 /16)
    br = width - bl

    top = int(height*3/9)
    bottom = height

    equation1 = equation_finder((bl, bottom), (ul, top) )
    equation2 = equation_finder((br, bottom), (ur, top) )

    return [equation1, equation2, bl, br, ul, ur, top]

def is_in_road(centroid, equations, height, width):

    _, _, bl, br, ul, ur, top = equations

    m1,c1 = equations[0]
    m2,c2 = equations[1]

    x = centroid[0]
    y = centroid[1]
    
    # if x < bl or x > br:
    #     return False
    
    # if y < top: 
    #     return False

    if centroid[1] < height //3 :
        return False

    if x <= width/2:
        exp_y = m1*x + c1
    
    else:
        exp_y = m2*x + c2
     
   
    
    if y > exp_y:
        # print(f"Point is {centroid}")
        # print(f"Lines are {equations}")
        # print(f"Expected is {exp_y}")
        # print(f"Real is {y}")

        return True
    
    return False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to broker.")
        #client.subscribe("esp8266/data_collection/esp8266-client-wemos/out")
    else:
        print("Connection failed with code: %d." % rc)

def setup(hostname):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(hostname)
    client.loop_start()
    return client

client = setup("192.168.139.156")

def rescale_frame(frame, percent=75):
    width = int(frame.shape[1] * percent/ 100)
    height = int(frame.shape[0] * percent/ 100)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation =cv2.INTER_AREA)

prevMaxBoxSize = 0
maxBoxSize = 0  
while True:
    img = capture.read()
    maxBoxSize = 0
    # img = cv2.imread('test2.jpg')
    img = rescale_frame(img, percent = 40)
    height, width, _ = img.shape

    if EQUATIONS is None:
        EQUATIONS = road_equation(width, height)

    cx, cy = width//2, height//2
    half = int(width * WIDTH_BOUND)
    # left_bound, right_bound = cx - half//2, cx + half//2
    # #we bound our x by threshold value
    # img = img[0: height,left_bound:right_bound]

    blob = cv2.dnn.blobFromImage(img, 1/255, (416, 416), (0,0,0), swapRB=True, crop=False)
    net.setInput(blob)
    output_layers_names = net.getUnconnectedOutLayersNames()
    layerOutputs = net.forward(output_layers_names) 

    boxes = []
    confidences = []
    class_ids = []

    for output in layerOutputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.2:
                center_x = int(detection[0]*width)
                center_y = int(detection[1]*height)

                w = int(detection[2]*width)
                h = int(detection[3]*height)

                x = int(center_x - w/2)
                y = int(center_y - h/2)

                boxes.append([x, y, w, h])
                confidences.append((float(confidence)))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.2, 0.4)

    if len(indexes)>0:
        for i in indexes.flatten():
            x, y, w, h = boxes[i]
            cx = x+w//2
            cy = y + h//2
            if is_in_road((cx, cy), EQUATIONS, height, width):
                cv2.putText(img, f"{(cx,cy)}in range", (x, y+20), font, 2, (255,255,255), 2)
                label = str(classes[class_ids[i]])
                if label == "car":
                    maxBoxSize = max(w*h, 0)
                confidence = str(round(confidences[i],2))
                color = colors[i]
                cv2.rectangle(img, (x,y), (x+w, y+h), color, 2)
            # cv2.putText(img, label + " " + confidence + f' size is {w}*{h}', (x, y+20), font, 2, (255,255,255), 2)


    if prevMaxBoxSize != 0:
        ratio = maxBoxSize / prevMaxBoxSize
        if ratio >= DANGER_THRESHOLD and ratio <= 1.73  : #to prevent from nth to something
            print("VERY DANGEROUS CAR Approaching")
            print("Prev max box size is" + str(prevMaxBoxSize))
            print("Max box size is" + str(maxBoxSize))
            cv2.putText(img, "DANGER", (width//2, height//2), font, 2, (255,255,255), 2)
            # requests.get(f"{WEMOS_IP}/dangerous")
            client.publish("esp8266/car_led/esp8266-client-wemos/out", "car-danger")
            time.sleep(1.5)
        elif ratio >= BEWARE_THRESHOLD:
            print("Approaching")
            print("Prev max box size is" + str(prevMaxBoxSize))
            print("Max box size is" + str(maxBoxSize))
            client.publish("esp8266/car_led/esp8266-client-wemos/out", "car-approaching")
            # requests.get(f"{WEMOS_IP}/approaching")

        elif maxBoxSize >= MAX_SIZE * (width*height):
            print("Very close to you")
            client.publish("esp8266/car_led/esp8266-client-wemos/out", "car-near")
            # requests.get(f"{WEMOS_IP}/near")
        else:
            print("Safe")
            client.publish("esp8266/car_led/esp8266-client-wemos/out", "car-safe")
            # requests.get(f"{WEMOS_IP}/safe")


    prevMaxBoxSize = maxBoxSize

    cv2.imshow('Image', img)
    key = cv2.waitKey(1)
    # if key == 27:
    #     cv2.destroyAllWindos()
    if key==27:
        break

capture.release()
cv2.destroyAllWindows()