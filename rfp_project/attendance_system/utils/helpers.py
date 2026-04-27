import numpy as np
import pickle

def encoding_to_blob(encoding_array):
    """
    Converts a numpy array face encoding to a binary BLOB for database storage.
    """
    return pickle.dumps(encoding_array)

def blob_to_encoding(blob_data):
    """
    Converts a binary BLOB from the database back to a numpy array face encoding.
    """
    return pickle.loads(blob_data)
