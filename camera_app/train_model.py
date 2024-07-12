from ultralytics import YOLO

model = YOLO()
# ~ 500 epochs
result = model.train(data='/home/moreau/Train/zz/data.yaml', epochs=1, imgsz=640)