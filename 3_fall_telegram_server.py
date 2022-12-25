import os
from datetime import datetime, timedelta
import requests
import cv2
interval = timedelta(seconds= 5)
TOKEN = "5533789871:AAE_Ka2EdYXq5dCPqt1pwgLcONKvWucc5qk"

def get_video_list(time):
    videos_sorted = os.listdir('./recordings')
    videos_sorted = [file for file in videos_sorted if file.endswith(".avi") ]
    videos_sorted.sort()
    
    videos_sorted_replaced = [x.replace(".avi", "") for x in videos_sorted]
 
    print(videos_sorted_replaced)
    first = 0
    for i in range (len(videos_sorted_replaced)):
        video_time = datetime.strptime(videos_sorted_replaced[i], '%Y-%m-%d %H:%M:%S')
        if time > video_time and time - video_time < interval :
            first = i
            break
       
    if first == 0:
        return [videos_sorted[-1]]

    return videos_sorted[max(0, first-3): first + 1]
   
def merge_videos(directory, videos, output_name):
    # Create a new video
    cap = cv2.VideoCapture(directory+videos[0])
    videoWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    videoHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video = cv2.VideoWriter(output_name, cv2.VideoWriter_fourcc(*"mp4v"), 20.0,(videoWidth, videoHeight))

    # Write all the frames sequentially to the new video
    for v in videos:
        
        curr_v = cv2.VideoCapture(directory+v)
        while curr_v.isOpened():
            r, frame = curr_v.read()    # Get return value and curr frame of curr video
            if not r:
                break
            video.write(frame)          # Write the frame

    video.release()                     # Save the video

def get_recording(time):
    # time = time.curr()
    video_list = get_video_list(time)
    video_name = f"before_fall-{time}.mp4"
    merge_videos("./recordings/", video_list, video_name)
    print("Done")
    return video_name

def upload(video_name):
    # Set up variables for endpoints
    auth_url = "https://ws.api.video/auth/api-key"
    create_url = "https://ws.api.video/videos"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "apiKey": "OolNy9Y6ojyyR4Fgt1pOk9VhmGQ3HdopfXq01Nx7ymP"
    }

    response = requests.request("POST", auth_url, json=payload, headers=headers)
    response = response.json()
    token = response.get("access_token")
    print("Access Granted")

    auth_string = "Bearer " + token

    # Set up headers for authentication
    headers_bearer = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth_string
    }

    # Create a video container
    payload2 = {
        "title": f"Fall Detection - {video_name}" ,
        "description": "It was a bad fall"
    }

    response = requests.request("POST", create_url, json=payload2, headers=headers_bearer)
    response = response.json()
    videoId = response["videoId"]

    print(f"Video ID obtained {videoId}")

    # Create endpoint to upload video to
    upload_url = create_url + "/" + videoId + "/source"

    # Create upload video headers 
    headers_upload = {
        "Accept": "application/vnd.api.video+json",
        "Authorization": auth_string
    }

    file = {"file": open(video_name, "rb")}
    response = requests.request("POST", upload_url, files=file, headers=headers_upload)
    json_response = response.json()
    return json_response['assets']['mp4']

# def upload_tele(chat_id, video_name):
#     files = {'video': video_name}
#     url = f"https://api.telegram.org/bot{TOKEN}/sendVideo?chat_id={chat_id}"
#     print(requests.post(url, data=files).json()) # this sends the message

def get_chat_id():
   
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()
    print(response)

    id = requests.get(url).json()['result'][0]['message']['from']['id']
    print(id)
    return id

def send_message(chat_id, message):
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
    print(requests.get(url).json()) # this sends the message


def handle_fall():
    
    # id = get_chat_id()
    # time = datetime.strptime('2022-11-03 00:33:06', '%Y-%m-%d %H:%M:%S')
    time = datetime.now()
    message = f"Fall Detected at {time}. A video will be uploaded shortly." 
    send_message('@cs3237_fall_detector', message)
    
    video = get_recording(time)
    # link = upload_tele('@cs3237_fall_detector', video)
    link = upload(video)
    message = f"Moments before disaster: {link}" 
    send_message('@cs3237_fall_detector', message)

# handle_fall()
def handle_emergency():
    message = f"No response from rider. Calling emergency services." 
    send_message('@cs3237_fall_detector', message)

def handle_back_up():
    message = f"Rider responded. In safe condition" 
    send_message('@cs3237_fall_detector', message)



from flask import Flask

app = Flask(__name__)

@app.route('/fall')
def fall():
    handle_fall()
    return "Done"

@app.route('/emergency')
def emergency():
    handle_emergency()
    return "Done"

@app.route('/back-up')
def backup():
    handle_back_up()
    return "Done"

if __name__ == '__main__':
    # APP.run(host='0.0.0.0', port=5000, debug=True)
    app.run(debug=True)