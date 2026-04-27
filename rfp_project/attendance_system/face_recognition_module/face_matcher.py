import face_recognition
import numpy as np

def match_face(face_encoding, known_encodings, tolerance=0.5):
    """
    Compares a face encoding against a list of known encodings.
    Returns the index of the first match, or -1 if no match is found.
    """
    if not known_encodings:
        return -1
        
    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
    
    if len(face_distances) > 0:
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            return best_match_index
            
    return -1
