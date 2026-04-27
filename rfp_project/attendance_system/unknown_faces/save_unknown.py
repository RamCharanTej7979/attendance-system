import cv2
import os
from datetime import datetime
from config import UNKNOWN_FACES_DIR
from database.db_connection import get_connection
from utils.logger import app_logger

def log_unknown_face(frame, face_location):
    """
    Crops the unknown face from the frame, saves it with a timestamp,
    and records the event in the database.
    """
    top, right, bottom, left = face_location
    
    # Crop the face from the frame
    # Adding a small margin
    margin = 20
    h, w, _ = frame.shape
    y1, y2 = max(0, top - margin), min(h, bottom + margin)
    x1, x2 = max(0, left - margin), min(w, right + margin)
    
    face_image = frame[y1:y2, x1:x2]
    
    timestamp = datetime.now()
    filename = f"unknown_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    filepath = os.path.join(UNKNOWN_FACES_DIR, filename)
    
    try:
        # Note: CV2 uses BGR. Ensure passed frame is standard from webcam.
        # If frame is RGB (as used in face_recognition), convert it to BGR before save.
        bgr_image = cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, bgr_image)
        
        # Save to database
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            query = "INSERT INTO unknown_faces (image_path, timestamp) VALUES (%s, %s)"
            cursor.execute(query, (filepath, timestamp))
            conn.commit()
            conn.close()
            
        app_logger.warning(f"Unknown face logged and saved at {filepath}")
    except Exception as e:
        app_logger.error(f"Error logging unknown face: {e}")
