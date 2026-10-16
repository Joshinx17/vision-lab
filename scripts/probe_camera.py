"""Read ten real frames, release the device, and report dimensions/timing only."""
import json
import time
import cv2

capture = cv2.VideoCapture(0)
start = time.perf_counter()
frames = 0
shape = None
try:
    if not capture.isOpened():
        raise SystemExit('NOT VERIFIED: camera 0 could not be opened.')
    for _ in range(10):
        ok, frame = capture.read()
        if not ok:
            raise SystemExit('NOT VERIFIED: camera frame acquisition failed.')
        frames += 1
        shape = list(frame.shape)
    print(json.dumps({'camera_opened': True, 'frames_read': frames, 'shape': shape, 'elapsed_seconds': time.perf_counter() - start}))
finally:
    capture.release()
