import face_recognition

def detect_faces(rgb_frame):
    """
    Finds all face locations in a given RGB frame.
    Returns a list of tuples representing bounding boxes (top, right, bottom, left).
    """
    return face_recognition.face_locations(rgb_frame)
