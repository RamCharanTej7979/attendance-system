import face_recognition

def generate_face_encoding(rgb_image, face_location=None):
    """
    Returns the 128-dimension face encoding for the face in the image.
    If face_location is provided, it calculates encoding exactly for that bounding box.
    """
    if face_location:
        encodings = face_recognition.face_encodings(rgb_image, [face_location])
    else:
        encodings = face_recognition.face_encodings(rgb_image)
        
    if encodings:
        return encodings[0]
    return None
