import cv2
import os
from datetime import datetime
from config import Config
from face_module.face_detector import get_face_locations
from face_module.face_encoder import generate_face_encoding
from face_module.face_matcher import match_face
from database.db_operations import mark_attendance_db, log_unknown_face

# Dictionary to track unknown faces saved recently to avoid spamming the DB
recent_unknowns = set()

def process_attendance_frame(frame, known_student_data):
    """
    Processes a single BGR OpenCV frame.
    known_student_data should be a list of dictionaries with 'id', 'name', 'face_encoding', 'roll_no'.
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Get locations and encodings
    face_locations = get_face_locations(rgb_frame)
    
    if not known_student_data:
        known_encodings = []
    else:
        known_encodings = [student['face_encoding'] for student in known_student_data]
    
    for face_location in face_locations:
        top, right, bottom, left = face_location
        face_encoding = generate_face_encoding(rgb_frame, face_location)
        
        name = "Unknown"
        color = (0, 0, 255) # Red for unknown
        
        if face_encoding is not None:
            match_idx = match_face(face_encoding, known_encodings)
            
            if match_idx is not None:
                # Known Face
                student = known_student_data[match_idx]
                name = student['name']
                student_id = student['id']
                color = (0, 255, 0) # Green for known
                
                # Mark attendance
                # This will silently fail on Duplicate if already marked today
                mark_attendance_db(student_id)
            else:
                # Unknown Face detected
                # Crop and save it
                # Added simple throttle to avoid saving 30 frames per second of the same unknown session
                current_time = datetime.now()
                # Use string formatting to group by second to reduce duplicates
                time_str = current_time.strftime("%Y%m%d_%H%M%S")
                
                if time_str not in recent_unknowns:
                    recent_unknowns.add(time_str)
                    
                    filename = f"unknown_{time_str}.jpg"
                    filepath = os.path.join(Config.UNKNOWN_FACES_DIR, filename)
                    
                    # Crop face from BGR frame
                    padding = 20
                    crop_top = max(0, top - padding)
                    crop_bottom = min(frame.shape[0], bottom + padding)
                    crop_left = max(0, left - padding)
                    crop_right = min(frame.shape[1], right + padding)
                    
                    face_crop = frame[crop_top:crop_bottom, crop_left:crop_right]
                    
                    if face_crop.size != 0:
                        cv2.imwrite(filepath, face_crop)
                        # Save path to DB
                        # Use relative path or just filename for DB
                        log_unknown_face(filename)

        # Draw bounding box and label
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    return frame
