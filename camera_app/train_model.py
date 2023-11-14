from ultralytics import YOLO

model = YOLO()

result = model.train(data='/home/moreau/Downloads/face-detection.v15i.yolov8/data.yaml', epochs=1, imgsz=640)