## Description
Video streaming Django application. Consist of 3 parts:

1. **/camera_app/:** PyQt6 application for local computer. Process videostream and detecting objects utilizing [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics). If any object has been detected the app saves video. Connecting to `server/camera_conn/`
2. **/server/camera_conn/:** Microservice connecting camera_app and Django website
3. **/server/djbackend/:** Django website with opportunuties to watch live camera videostream, and get access to archive of recorded videos.

## Running Locally

Install with dependecies:

```bash
git clone https://github.com/SW895/CameraProject
pip install -r requirements.txt
```
Run server:

```bash
docker-compose -f server/docker-compose.prod.yaml up -d --build
```

Your app should now be running on `localhost:1337` (by default).

> [!NOTE] 
> In order to be able to watch videostream, get archive video and aproving registration you should also run camera application.
> 
>
>```bash
>python camera_app/run_app.py
>```


> [!IMPORTANT]
>
> By default:
> * Detection enabled
> * All users are allowed to register (no whitelist)
> * Application will use USB web-camera or builtin device 
> * Camera application settings located at: `/camera_app/settings.cfg`

> [!TIP]
> Specify camera:
> 1. In camera application settings section `[CAMERA_LIST]`
> 2. Replace default with format:
> 
> ```toml
> your_camera_name=your_camera_source
> ```

> [!TIP]
> Specify allowed users:
> 1. In camera application settings section `[USER_LIST]`
> 2. Set `ALLOWED_ALL` to `0`
> 3. Add allowed usernames to `APROVED_USER_LIST` seprated by space (ex: `user1 user2 user3`)

## Technology stack:

* PyQt6
* YOLOv8
* Django
* Celery
* Redis
* PostgreSQL
* PyTest
