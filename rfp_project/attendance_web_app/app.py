from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, jsonify
import cv2
import numpy as np
from config import Config
from database.db_connection import init_db
from database.db_operations import get_student_by_roll, add_student, get_all_student_encodings, get_student_dashboard_data
from attendance.mark_attendance import process_attendance_frame
from face_module.face_detector import get_face_locations
from face_module.face_encoder import generate_face_encoding
import atexit

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database when app starts
init_db()

# Global variables for camera streaming state
camera = None
student_encodings_cache = []

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera

def release_camera():
    global camera
    if camera is not None and camera.isOpened():
        camera.release()
        camera = None

atexit.register(release_camera)

def generate_attendance_stream():
    """Generator for marking attendance feed"""
    cam = get_camera()
    global student_encodings_cache
    student_encodings_cache = get_all_student_encodings()
    
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            # Process frame to detect faces and mark attendance
            frame = process_attendance_frame(frame, student_encodings_cache)
            
            # Encode frame to JPEG for web streaming
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def generate_raw_stream():
    """Generator for raw feed (used during add student preview)"""
    cam = get_camera()
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user_id = request.form.get('id')
        password = request.form.get('password')
        if user_id == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid Admin Credentials', 'error')
    return render_template('admin_login.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_no = request.form.get('id')
        password = request.form.get('password')
        # Simple Validation: Password = Roll Number
        if roll_no and password and roll_no == password:
            student = get_student_by_roll(roll_no)
            if student:
                session['student_logged_in'] = True
                session['roll_no'] = roll_no
                return redirect(url_for('student_dashboard'))
            else:
                flash('Student not found in database.', 'error')
        else:
            flash('Invalid Student Credentials. Check Roll Number.', 'error')
    return render_template('student_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/student_dashboard')
def student_dashboard():
    if not session.get('student_logged_in'):
        return redirect(url_for('student_login'))
    
    roll_no = session.get('roll_no')
    data = get_student_dashboard_data(roll_no)
    
    return render_template('student_dashboard.html', data=data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/attendance')
def attendance():
    # User requested: Mark Attendance Page
    return render_template('mark_attendance.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_attendance_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/raw_video_feed')
def raw_video_feed():
    return Response(generate_raw_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/add_student', methods=['GET'])
def add_student_view():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('add_student.html')

@app.route('/api/capture_and_add_student', methods=['POST'])
def capture_and_add_student():
    """
    Called via AJAX from Add Student page.
    It reads ONE frame from the camera, generates encoding, and adds to DB.
    """
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    name = request.form.get('name')
    roll_no = request.form.get('roll_no')
    
    if not name or not roll_no:
        return jsonify({"success": False, "message": "Name and Roll Number required."})
        
    # Check if student already exists
    if get_student_by_roll(roll_no):
        return jsonify({"success": False, "message": f"Student with roll {roll_no} already exists."})
        
    cam = get_camera()
    success, frame = cam.read()
    
    if not success:
        return jsonify({"success": False, "message": "Failed to read from camera."})
        
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = get_face_locations(rgb_frame)
    
    if len(face_locations) == 0:
        return jsonify({"success": False, "message": "No face detected in frame. Please stand clearly in front."})
    if len(face_locations) > 1:
        return jsonify({"success": False, "message": "Multiple faces detected. Only one person should be in frame."})
        
    face_encoding = generate_face_encoding(rgb_frame, face_locations[0])
    
    if face_encoding is None:
         return jsonify({"success": False, "message": "Could not generate face encoding."})
         
    # Add to DB
    if add_student(name, roll_no, face_encoding):
        # Refresh cache if attendance stream running
        global student_encodings_cache
        student_encodings_cache = get_all_student_encodings()
        return jsonify({"success": True, "message": f"Student {name} added successfully!"})
    else:
        return jsonify({"success": False, "message": "Database insertion failed."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
