import cv2
import numpy as np
from ultralytics import YOLO
import requests
import time

# ---------------------------
# Load YOLOv8 Model
# ---------------------------
model = YOLO('yolov8s.pt')  # or 'yolov8n.pt' for faster but less accurate


# ---------------------------
# Helper Functions
# ---------------------------
def bbox_iou(boxA, boxB):
    """Compute IoU between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    inter = interW * interH
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union = max(1e-6, areaA + areaB - inter)
    return inter / union


def calc_color_hist(img, bbox):
    """Compute normalized HSV color histogram of the cropped region."""
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = max(1, int(x2)), max(1, int(y2))
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return np.zeros(512)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def hist_similarity(h1, h2):
    """Compare two histograms using correlation (1 = identical)."""
    if h1 is None or h2 is None or h1.size == 0 or h2.size == 0:
        return -1.0
    return float(cv2.compareHist(h1.astype(np.float32), h2.astype(np.float32), cv2.HISTCMP_CORREL))


# ---------------------------
# Passenger Counting Function
# ---------------------------
def count_passengers(video_path, zone, direction="board", display=False, debug=True):
    """
    Counts people entering or exiting a zone in the video.
    Prevents double-counting by using color histogram re-identification.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error opening video: {video_path}")
        return 0

    ret, frame = cap.read()
    if not ret:
        print(f"⚠️ No frames found in {video_path}")
        return 0
    height, width = frame.shape[:2]
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    # Zone
    ZONE_X1, ZONE_Y1, ZONE_X2, ZONE_Y2 = zone

    # Trackers
    active_tracks = {}
    lost_tracks = {}
    next_id = 1
    count = 0
    frame_idx = 0

    print(f"▶️ Processing video: {video_path}")
    print(f"   Zone: {zone}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run YOLO per frame
        results = model(frame, conf=0.4, imgsz=640)
        dets = []
        r = results[0]
        if hasattr(r, 'boxes') and r.boxes is not None:
            boxes = r.boxes.xyxy.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy()
            for box, cls in zip(boxes, classes):
                if int(cls) != 0:  # only person class
                    continue
                dets.append({"bbox": list(map(int, box))})

        # ---------------------------
        # Match detections to existing tracks
        # ---------------------------
        assigned_dets = [-1] * len(dets)
        for t_id, tr in list(active_tracks.items()):
            best_iou = 0
            best_det = -1
            for i, d in enumerate(dets):
                if assigned_dets[i] != -1:
                    continue
                iou = bbox_iou(tr['bbox'], d['bbox'])
                if iou > best_iou:
                    best_iou, best_det = iou, i
            if best_iou > 0.4:
                d = dets[best_det]
                hist = calc_color_hist(frame, d['bbox'])
                cx = (d['bbox'][0] + d['bbox'][2]) // 2
                cy = (d['bbox'][1] + d['bbox'][3]) // 2
                tr['bbox'] = d['bbox']
                tr['hist'] = hist
                tr['centroids'].append((cx, cy))
                tr['last_frame'] = frame_idx
                tr['age'] += 1
                assigned_dets[best_det] = t_id
                if debug:
                    print(f"[Frame {frame_idx}] ✅ Matched track {t_id} (IoU={best_iou:.2f})")

        # ---------------------------
        # Re-identify or create new tracks
        # ---------------------------
        for i, d in enumerate(dets):
            if assigned_dets[i] != -1:
                continue
            hist = calc_color_hist(frame, d['bbox'])
            best_sim = -1
            best_id = None
            # try match with lost tracks
            for lid, ltr in list(lost_tracks.items()):
                if frame_idx - ltr['last_frame'] > 50:
                    del lost_tracks[lid]
                    continue
                sim = hist_similarity(hist, ltr['hist'])
                if sim > best_sim:
                    best_sim = sim
                    best_id = lid
            if best_sim > 0.45:
                tr = lost_tracks.pop(best_id)
                tr['bbox'] = d['bbox']
                tr['hist'] = hist
                cx = (d['bbox'][0] + d['bbox'][2]) // 2
                cy = (d['bbox'][1] + d['bbox'][3]) // 2
                tr['centroids'].append((cx, cy))
                tr['last_frame'] = frame_idx
                active_tracks[best_id] = tr
                assigned_dets[i] = best_id
                if debug:
                    print(f"[Frame {frame_idx}] 🔄 ReID match: old ID {best_id}, sim={best_sim:.2f}")
            else:
                tid = next_id
                next_id += 1
                cx = (d['bbox'][0] + d['bbox'][2]) // 2
                cy = (d['bbox'][1] + d['bbox'][3]) // 2
                active_tracks[tid] = {
                    "bbox": d['bbox'],
                    "hist": hist,
                    "centroids": [(cx, cy)],
                    "last_frame": frame_idx,
                    "age": 1,
                    "counted": False
                }
                assigned_dets[i] = tid
                if debug:
                    print(f"[Frame {frame_idx}] 🆕 New track {tid} created.")

        # ---------------------------
        # Move old tracks to lost
        # ---------------------------
        to_remove = []
        for t_id, tr in active_tracks.items():
            if frame_idx - tr['last_frame'] > 5:
                lost_tracks[t_id] = tr
                to_remove.append(t_id)
        for rid in to_remove:
            if debug:
                print(f"[Frame {frame_idx}] ⚠️ Track {rid} lost temporarily.")
            del active_tracks[rid]

        # ---------------------------
        # Count logic
        # ---------------------------
        for t_id, tr in active_tracks.items():
            if tr['counted'] or tr['age'] < 6:
                continue
            cy_now = tr['centroids'][-1][1]
            cy_prev = tr['centroids'][0][1]
            cx_now = tr['centroids'][-1][0]
            inside_zone = (ZONE_X1 < cx_now < ZONE_X2) and (ZONE_Y1 < cy_now < ZONE_Y2)
            move = cy_now - cy_prev
            if inside_zone:
                if direction == "board" and move > 10:
                    tr['counted'] = True
                    count += 1
                    if debug:
                        print(f"[Frame {frame_idx}] 🟢 Counted ID {t_id} boarding.")
                elif direction == "alight" and move < -10:
                    tr['counted'] = True
                    count += 1
                    if debug:
                        print(f"[Frame {frame_idx}] 🔵 Counted ID {t_id} alighting.")

        # ---------------------------
        # Visualization
        # ---------------------------
        vis = frame.copy()
        cv2.rectangle(vis, (ZONE_X1, ZONE_Y1), (ZONE_X2, ZONE_Y2), (255, 0, 0), 2)
        cv2.putText(vis, f"Count: {count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        for t_id, tr in active_tracks.items():
            x1, y1, x2, y2 = tr['bbox']
            color = (0, 255, 0) if tr['counted'] else (0, 255, 255)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cx, cy = tr['centroids'][-1]
            cv2.putText(vis, f"ID{t_id}", (cx, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if display:
            cv2.imshow("Passenger Counting", vis)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        frame_idx += 1


    cap.release()
    if display:
        cv2.destroyAllWindows()

    print("------------------------------------------------")
    print(f"✅ Final {direction} count from {video_path}: {count}")
    print(f"   Active tracks: {len(active_tracks)}, Lost tracks: {len(lost_tracks)}")
    print("------------------------------------------------")
    return count


# ---------------------------
# MAIN SIMULATION
# ---------------------------
bus_capacity = 10
total_seats = 42

boarding_zone = (0, 450, 2000, 1000)
alighting_zone = (0, 350, 1800, 1000)

boarding_count = count_passengers(
    r"C:\Academics\AI_Project\bus_backend\videos\up.mp4",
    boarding_zone,
    direction="board",
    display=True
)

alighting_count = count_passengers(
    r"C:\Academics\AI_Project\bus_backend\videos\down2.mp4",
    alighting_zone,
    direction="alight",
    display=True
)

bus_capacity = bus_capacity + boarding_count - alighting_count
available_seats = total_seats - bus_capacity

print("\n📊 Final Report")
print(f"✅ People Boarded = {boarding_count}")
print(f"🚪 People Alighted = {alighting_count}")
print(f"👥 Current Bus Capacity = {bus_capacity}")
print(f"💺 Available Seats = {available_seats}/{total_seats}")

# ---------------------------
# SEND RESULTS TO FLASK BACKEND
# ---------------------------
try:
    response = requests.post("http://192.168.101.241:5000/update_seats", json={
        "bus_id": "BusA",
        "boarded": boarding_count,
        "alighted": alighting_count
    })
    if response.status_code == 200:
        print("✅ Data sent to backend:", response.json())
    else:
        print("⚠️ Backend responded with:", response.status_code, response.text)
except Exception as e:
    print("⚠️ Could not send data to backend:", e)
