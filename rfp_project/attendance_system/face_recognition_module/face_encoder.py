import face_recognition

def encode_faces(rgb_frame, face_locations):
    """
    Computes face encodings for all detected face locations in the frame.
    Returns a list of numpy arrays (the encodings).
    """
    return face_recognition.face_encodings(rgb_frame, face_locations)
