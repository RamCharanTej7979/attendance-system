import face_recognition
import numpy as np

def match_face(unknown_encoding, known_encodings_list, tolerance=0.6):
    """
    Compares the unknown face encoding against a list of known face encodings.
    Returns the index of the matched face in the list, or None if no match found.
    """
    if len(known_encodings_list) == 0:
        return None
        
    matches = face_recognition.compare_faces(known_encodings_list, unknown_encoding, tolerance=tolerance)
    face_distances = face_recognition.face_distance(known_encodings_list, unknown_encoding)
    
    if len(face_distances) > 0:
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            return best_match_index
            
    return None
