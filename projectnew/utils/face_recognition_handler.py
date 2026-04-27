import face_recognition
import cv2
import numpy as np
import base64

# Global dictionary to track anti-switching smoothing
_session_locks = {}
_TRACK_COOLDOWN = 3

def encode_face_from_base64(base64_string, known_encodings=None, threshold=0.28):
    """
    Decodes base64 string image and returns face encoding.
    Ensures correct float64 type architecture logic bounds.
    """
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    
    try:
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None, "Invalid image data."
            
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image, model="hog") # hog is safer for cpu
        
        if not face_locations:
            return None, "No face found in the image."
        
        if len(face_locations) > 1:
            return None, "Multiple faces found. Please ensure only one face is in the frame."
            
        face_encoding = face_recognition.face_encodings(rgb_image, face_locations)[0]
        test_encoding = np.array(face_encoding, dtype=np.float64)
        
        # 1. Normalize Encoding
        norm = np.linalg.norm(test_encoding)
        if norm > 0:
            test_encoding = test_encoding / norm
            
        # 2. Registration Safety Upgrade (Duplicates/Ambiguity)
        if known_encodings is not None and len(known_encodings) > 0:
            known_array = np.array(known_encodings, dtype=np.float64)
            
            # Normalize target array
            norms = np.linalg.norm(known_array, axis=1, keepdims=True)
            known_array = np.divide(known_array, norms, out=np.zeros_like(known_array), where=norms!=0)
            
            distances = face_recognition.face_distance(known_array, test_encoding)
            
            if len(distances) > 0:
                min_dist = np.min(distances)
                if min_dist <= threshold:
                    return None, "Registration Rejected: Exact duplicate face found in database."
                if min_dist <= 0.45:
                    return None, "Registration Rejected: Face is too mathematically similar to another student."
                    
        return test_encoding, "Success"
    except Exception as e:
        return None, f"Encoding failed: {str(e)}"

def recognize_faces(frame, known_face_encodings, known_face_ids, threshold=0.28):
    """
    Detects faces in the frame and compares them to known encodings safely.
    Implements normalization, extreme precision thresholds, and anti-switching temporal locks.
    """
    try:
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        
        # Convert the image from BGR color (OpenCV output) to RGB color
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find all the faces and face encodings in current frame
        face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        recognized_people = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            student_id = None
            
            # Scale back up face locations since they were detected on 1/4 frame
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            
            if known_face_encodings:
                test_encoding = np.array(face_encoding, dtype=np.float64)
                
                # Normalize Test
                t_norm = np.linalg.norm(test_encoding)
                if t_norm > 0:
                    test_encoding = test_encoding / t_norm
                
                # Normalize Known
                known_array = np.array(known_face_encodings, dtype=np.float64)
                k_norms = np.linalg.norm(known_array, axis=1, keepdims=True)
                known_array = np.divide(known_array, k_norms, out=np.zeros_like(known_array), where=k_norms!=0)
                
                face_distances = face_recognition.face_distance(known_array, test_encoding)
                
                if len(face_distances) > 0:
                    sorted_indices = np.argsort(face_distances)
                    best_match_index = sorted_indices[0]
                    best_distance = face_distances[best_match_index]
                    
                    if best_distance <= threshold:
                        # Ambiguity resolution
                        if len(face_distances) > 1:
                            second_best_index = sorted_indices[1]
                            second_best_distance = face_distances[second_best_index]
                            
                            # If not clearly separated, treat as UNKNOWN
                            if (second_best_distance - best_distance) < 0.10:
                                student_id = None
                            else:
                                student_id = known_face_ids[best_match_index]
                        else:
                            student_id = known_face_ids[best_match_index]
            
            # Spatial Anti-switching Safety Rule
            global _session_locks
            import time as tm
            current_t = tm.time()
            
            spatial_key = (top // 50, left // 50)
            
            if spatial_key in _session_locks and current_t < _session_locks[spatial_key]['lock_until']:
                locked_id = _session_locks[spatial_key]['student_id']
                if student_id is not None and student_id != locked_id:
                    # Prevent identity switching within this spatial region
                    student_id = None
                elif student_id == locked_id:
                    # Refresh lock
                    _session_locks[spatial_key]['lock_until'] = current_t + _TRACK_COOLDOWN
                elif student_id is None:
                    # We have a valid lock, but no strong ID found. User explicitly requested:
                    # "No soft matching ... No forced assignment ... If confusion exists -> mark as UNKNOWN"
                    # Thus we strictly hold UNKNOWN instead of blindly forcing the old ID.
                    pass
            else:
                # establish new lock if confidently recognized
                if student_id is not None:
                    _session_locks[spatial_key] = {
                        'student_id': student_id,
                        'lock_until': current_t + _TRACK_COOLDOWN
                    }
                    
            # Clean up old locks
            stale_keys = []
            for k, v in _session_locks.items():
                if current_t > v['lock_until']:
                    stale_keys.append(k)
            for k in stale_keys:
                del _session_locks[k]
            recognized_people.append({
                'student_id': student_id,
                'location': (top, right, bottom, left),
                'encoding': face_encoding
            })
            
        return recognized_people
    except Exception:
        # On video failure stream, safe bypass
        return []
