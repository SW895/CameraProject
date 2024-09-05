# CameraProject

### Description
Online video streaming DJANGO APP.

1. /camera_app/: PyQt6 application for local computer. Process videostream and detecting objects utilizing Ultralytics YOLOv8. If any object detected saves video. Connecting to server/camera_conn/
2. /server/camera_conn/: microservice connecting camera_app and Django website
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

run camera app:
```
python run_app.py
```

### Technology stack:

* PyQt6
* YOLOv8
* Dajngo
* Celery
* Redis
* PostgreSQL