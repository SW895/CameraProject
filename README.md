### Description
Video streaming Django application. Consist of 3 parts:

1. /camera_app/: PyQt6 application for local computer. Process videostream and detecting objects utilizing [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics). If any object detected saves video. Connecting to server/camera_conn/
2. /server/camera_conn/: Microservice connecting camera_app and Django website
3. /server/djbackend/: Django website with opportunuties to watch live camera videostream, and get access to archive of recorded videos.

### Running Locally
```
git clone https://github.com/SW895/CameraProject
pip install -r requirements.txt
```
run server:
```
docker-compose -f server/docker-compose.prod.yaml up -d --build
```
Your app should now be running on localhost:1337.

> [!NOTE] 
> In order to be able to watch videostream, get arhive video and aproving registration you should also run camera application.
> 
>```
>python camera_app/run_app.py
>```

> [!IMPORTANT]
> * Detection enabled by default.
> * All users are allowed to register by default.
> * By default application will use USB web-camera or builtin. 
> * Camera application settings located at: /camera_app/settings.cfg

> [!TIP]
> Specify camera:
> 1. In camera application settings section [CAMERA_LIST]
> 2. Replace default with format: 
> ```
> your_camera_name=your_camera_source
> ```

> [!TIP]
> Specify allowed users:
> 1. In camera application settings section [USER_LIST]
> 2. Set ALLOWED_ALL to 0
> 3. Add allowed usernames to APROVED_USER_LIST divided by space

### Technology stack:

* PyQt6
* YOLOv8
* Dajngo
* Celery
* Redis
* PostgreSQL