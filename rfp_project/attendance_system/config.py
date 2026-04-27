import os

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-cvr'
    DEBUG = True
    
    # Database settings
    DB_HOST = 'localhost'
    DB_PORT = 3306
    DB_USER = 'root'
    DB_PASSWORD = ''
    DB_NAME = 'attendance_db'
    
    # App Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UNKNOWN_FACES_DIR = os.path.join(BASE_DIR, 'unknown_faces')
    
    # Ensure directories exist
    if not os.path.exists(UNKNOWN_FACES_DIR):
        os.makedirs(UNKNOWN_FACES_DIR)

    # Attendance Logic Rules
    TOTAL_WORKING_DAYS = 25
