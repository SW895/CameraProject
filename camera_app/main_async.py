from ultralytics import YOLO
import cv2
from datetime import date, datetime
import os
import asyncio
import socket
import threading
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
import queue

#========================================================================

frames_to_save = []
empty_frame_counter = 0
detection = False


path = os.path.abspath(os.path.dirname(__file__))
model_path = path + '/weights/test_weights.pt'
save_path = path[0:(len(path)-10)]+'video_archive/'

model = YOLO(model_path)
cap = cv2.VideoCapture(-1)

#frame_queue = asyncio.Queue(maxsize=1)
frame_queue = queue.Queue(maxsize=1)

#========================================================================

async def save_video(frames_to_save, width, height):
    today = date.today()
    today_save_path = save_path + today.strftime("%d_%m_%Y") + '/'
    
    if not os.path.isdir(today_save_path):
        os.mkdir(today_save_path)

    current_date = datetime.now()
    video_name = os.path.join(today_save_path,current_date.strftime("%d_%m_%Y_%H_%M_%S") + '.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_name, fourcc, 10.0, (width, height))

    for frames in frames_to_save:
        out.write(frames)

    await asyncio.sleep(10)

    #TODO 
    #save to django model

#========================================================================
#def start():
def start():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(('127.0.0.1',12345))
    serversocket.listen(5)
    print('socket connected')

    while True:
        try:
            print('try connection')
            (clientsocket, adress) = serversocket.accept()
            print('connection established')
            #while cap.isOpened():
            while True:
                frame = frame_queue.get() 
                print('frame from queue')
                ret, jpeg = cv2.imencode('.jpg', frame)
                data_bytes = jpeg.tobytes()
                clientsocket.send(data_bytes)
            #frame_queue.task_done()
        except BrokenPipeError:
            pass
        except ConnectionResetError:
            pass
#========================================================================
async def start_server():
    server = await asyncio.start_server(stream_server, '127.0.0.1', 12345)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()

async def stream_server(reader, writer):

    """
    try:
        while True:
            data = (await reader.readline()).decode().strip()
            if not data:
                print('disconnectide')
                break
            print('wait fo frame')
            frame = await frame_queue.get() 
            print('frame from queue')
            ret, jpeg = cv2.imencode('.jpg', frame)
            data_bytes = jpeg.tobytes()
            writer.write(data_bytes)
            await writer.drain()
    except ConnectionResetError:
        pass
    """
 
    while True:

        data = (await reader.readline()).decode().strip()
        if not data:
            print('disconnected')
            break
        print('wait fo frame')
        frame = await frame_queue.get() 
        print('frame from queue')
        ret, jpeg = cv2.imencode('.jpg', frame)
        data_bytes = jpeg.tobytes()
        writer.write(data_bytes)
        await writer.drain()
 
    #print('Close connection')
    #writer.close()
    #await writer.wait_closed()

#========================================================================
def detection():
    frames_to_save = []
    empty_frame_counter = 0
    detection = False
    a,frame_size = cap.read()
    height, width, channels = frame_size.shape

    while cap.isOpened():

        success, frame = cap.read()        

        if success:
            results = model(frame,conf=0.5)

            if results[0]:
                empty_frame_counter = 0
                detection = True
                annotated_frame = results[0].plot()            
            else:
                if detection:
                    empty_frame_counter += 1
                annotated_frame = frame
            print('add frame to queue')

            #await frame_queue.put(annotated_frame)
            """
            try:
                frame_queue.put_nowait(annotated_frame)                
                print('fraim added')
            except asyncio.QueueFull:
                print('queue full')
                #await asyncio.sleep(1)
            """
            if frame_queue.empty():
                print('add frame to queue')
                frame_queue.put(annotated_frame)
            else:
                print('queue full')
           
            
            cv2.imshow("YOLOv8 Inference", annotated_frame)

            if detection:
                frames_to_save.append(annotated_frame)

            if empty_frame_counter > 20 and detection == True:
                #asyncio.create_task(save_video(frames_to_save[:], width, height))
            
                frames_to_save = []
                detection = False
                #break
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break

async def main(): 
    loop = asyncio.get_running_loop()
    awaitable = loop.run_in_executor(None, detection)
    #server = await asyncio.start_server(stream_server, '127.0.0.1', 12345)
    #addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    start()
    #print(f'Serving on 12345')
    #async with server:
        #await server.serve_forever()
    await awaitable
    
    


#from concurrent.futures import ProcessPoolExecutor
#loop = asyncio.get_event_loop()
#p = ProcessPoolExecutor(1) # Create a ProcessPool with 2 processes
#loop.run_until_complete(main())

asyncio.run(main())
#asyncio.run(send_stream())

#t2.join()
cap.release()
cv2.destroyAllWindows()

