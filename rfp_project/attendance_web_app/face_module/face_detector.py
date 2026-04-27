import face_recognition

def get_face_locations(rgb_image):
    """
    Returns an array of bounding boxes of human faces in a image
    """
    return face_recognition.face_locations(rgb_image)
