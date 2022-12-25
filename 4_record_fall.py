import numpy as np
import cv2 as cv
from datetime import datetime,timedelta
cap = cv.VideoCapture("http://172.25.96.28:8080/video")
# Define the codec and create VideoWriter object
fourcc = cv.VideoWriter_fourcc('M','J','P','G')

curr = datetime.now()
videoWidth = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
videoHeight = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
curr_str = curr.strftime('%Y-%m-%d %H:%M:%S')
print(curr_str)
out = cv.VideoWriter(f'./recordings/{curr_str}.avi', fourcc, 20.0, (videoWidth,  videoHeight))
time = datetime.now()
difference = timedelta(seconds = 8)

import os

def delete_videos():
    videos_sorted = os.listdir('./recordings')
    
    if len(videos_sorted) < 30:
        print("nothing")
        return
    
    videos_sorted.sort()
    for i in range (len(videos_sorted) - 10):
        os.remove('./recordings/'+ videos_sorted[i])
    
    print("removed")

while cap.isOpened():
    curr = datetime.now()
    # print(curr - time)
    if (curr - time) >= difference:
        out.release()
        print("written")
        curr_str = curr.strftime('%Y-%m-%d %H:%M:%S')
        print(curr_str)
        delete_videos()
        out = cv.VideoWriter(f'./recordings/{curr_str}.avi', fourcc, 20.0, (videoWidth,  videoHeight))
        time = datetime.now()
    
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break

    out.write(frame)
    # cv.imshow('frame', frame)
    if cv.waitKey(1) == ord('q'):
        break


# Release everything if job is finished
cap.release()
out.release()
cv.destroyAllWindows()