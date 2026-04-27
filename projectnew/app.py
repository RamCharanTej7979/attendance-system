import os
import cv2
import datetime
import time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response

from models.db import (
    init_db, add_student, get_all_students_encodings, get_student_by_roll, 
    get_all_students, mark_attendance, get_attendance_records, 
    get_student_attendance, get_unknown_faces, save_unknown_face, get_connection, delete_student
)
from utils.face_recognition_handler import encode_face_from_base64, recognize_faces

app = Flask(__name__)
# In a real app, use environment variables
app.secret_key = 'super_secret_key_attendance_ai_system_2026'

# Initialize DB completely
init_db()

# --- Memory Cache for Attendance Optimization ---
ALREADY_MARKED_TODAY = set()
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# --- Camera Singleton ---
class CameraSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cv2.VideoCapture(0)
            if not cls._instance.isOpened():
                cls._instance = None
        return cls._instance

# Application Variables
LAST_UNKNOWN_SAVE = 0
UNKNOWN_SAVE_COOLDOWN = 5 # seconds

# --- Authentication Helpers ---
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash("Please log in as admin to access this page.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'student_id' not in session:
            flash("Please log in to view your dashboard.", "error")
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return wrapper

def attendance_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('attendance_access'):
            flash("Please enter the kiosk password to unlock the attendance terminal.", "error")
            return redirect(url_for('attendance_login'))
        return f(*args, **kwargs)
    return wrapper


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Hardcoded credentials as per a common admin setup
        if username == 'admin' and password == 'admin':
            session['admin_logged_in'] = True
            flash("Logged in successfully.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials. Try admin / admin.", "error")
            
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    students = get_all_students()
    attendance = get_attendance_records()
    unknown_faces = get_unknown_faces()
    return render_template('admin_dashboard.html', students=students, attendance=attendance, unknown_faces=unknown_faces)


@app.route('/admin/add_student', methods=['GET', 'POST'])
@admin_required
def admin_add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        photo_data = request.form.get('photo_data')
        
        if not photo_data:
            flash("Please capture a photo before submitting.", "error")
            return redirect(url_for('admin_add_student'))
            
        encoding, msg = encode_face_from_base64(photo_data)
        
        if encoding is None:
            flash(msg, "error")
        else:
            success, db_msg = add_student(name, roll_number, encoding)
            if success:
                flash(f"Student {name} added successfully!", "success")
                return redirect(url_for('admin_dashboard'))
            else:
                flash(db_msg, "error")
                
    return render_template('admin_add_student.html')


@app.route('/admin/delete_student/<int:student_id>', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    success, msg = delete_student(student_id)
    if success:
        # Prevent old ID cache hit if re-registering
        global ALREADY_MARKED_TODAY
        ALREADY_MARKED_TODAY = set([k for k in ALREADY_MARKED_TODAY if not k.startswith(f"{student_id}_")])
        flash(msg, "success")
    else:
        flash(msg, "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        student = get_student_by_roll(roll_number)
        
        if student:
            session['student_id'] = student['id']
            session['student_name'] = student['name']
            flash(f"Welcome back, {student['name']}", "success")
            return redirect(url_for('student_dashboard'))
        else:
            flash("Roll number not found in database.", "error")
            
    return render_template('student_login.html')

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    student_id = session.get('student_id')
    
    # Bring in connection to fetch base details safely
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        student_row = cursor.fetchone()
    finally:
        conn.close()
            
    student = dict(student_row) if student_row else {}
    
    attendance_records, summary = get_student_attendance(student_id)
    return render_template('student_dashboard.html', student=student, attendance=attendance_records, summary=summary)


@app.route('/student/logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))


@app.route('/attendance_login', methods=['GET', 'POST'])
def attendance_login():
    if request.method == 'POST':
        password = request.form.get('password')
        
        if password == 'admin':
            session['attendance_access'] = True
            flash("Attendance terminal unlocked successfully.", "success")
            return redirect(url_for('mark_attendance_page'))
        else:
            flash("Incorrect Password", "error")
                
    return render_template('attendance_login.html')

@app.route('/attendance_logout')
def attendance_logout():
    session.pop('attendance_access', None)
    flash("Attendance terminal locked effectively.", "success")
    return redirect(url_for('index'))

@app.route('/attendance')
@attendance_required
def mark_attendance_page():
    return render_template('mark_attendance.html')

def gen_frames(purpose='capture'):
    global LAST_UNKNOWN_SAVE, CURRENT_DATE, ALREADY_MARKED_TODAY
    
    camera = CameraSingleton.get_instance()
    if camera is None:
        # Camera not found, yield empty stream or placeholder
        return
    
    students = []
    known_encodings = []
    known_ids = []
    known_names = {}
    
    if purpose == 'attendance':
        # Pre-fetch strictly once per generator loop load
        students = get_all_students_encodings()
        known_encodings = [s['encoding'] for s in students]
        known_ids = [s['id'] for s in students]
        known_names = {s['id']: (s['name'], s['roll_number']) for s in students}
    
    while True:
        success, frame = camera.read()
        if not success:
            break
            
        if purpose == 'attendance':
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            # Reset cache automatically across midnight
            if date_str != CURRENT_DATE:
                CURRENT_DATE = date_str
                ALREADY_MARKED_TODAY.clear()
            
            recognized = recognize_faces(frame, known_encodings, known_ids, threshold=0.5)
            
            has_unknown = False
            for r in recognized:
                top, right, bottom, left = r['location']
                student_id = r['student_id']
                
                if student_id is not None:
                    # Valid Student
                    cv2.rectangle(frame, (left, top), (right, bottom), (255, 200, 0), 2)
                    name, roll = known_names.get(student_id, ("Unknown", "N/A"))
                    label = f"{name} ({roll})"
                    cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                    
                    # Caching system to prevent extreme DB overloading
                    cache_key = f"{student_id}_{date_str}"
                    if cache_key not in ALREADY_MARKED_TODAY:
                        success_mark, msg = mark_attendance(student_id, date_str, time_str)
                        if success_mark:
                            ALREADY_MARKED_TODAY.add(cache_key)
                            
                    if cache_key in ALREADY_MARKED_TODAY:
                        cv2.putText(frame, "Present Today", (left, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                else:
                    # Unknown Person
                    has_unknown = True
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                    
            # Safe caching for unknown person to prevent HDD spam
            current_time = time.time()
            if has_unknown and (current_time - LAST_UNKNOWN_SAVE) > UNKNOWN_SAVE_COOLDOWN:
                # Strictly limit unknown faces
                if len(get_unknown_faces()) >= 30:
                    print("Unknown face limit reached (30). Skipping save.")
                else:
                    LAST_UNKNOWN_SAVE = current_time
                    os.makedirs(os.path.join('static', 'images', 'unknown'), exist_ok=True)
                    filename = f"unknown_{date_str}_{now.strftime('%H%M%S')}.jpg"
                    filepath = os.path.join('static', 'images', 'unknown', filename)
                    cv2.imwrite(filepath, frame)
                    
                    rel_path = f"images/unknown/{filename}"
                    save_unknown_face(rel_path, f"{date_str} {time_str}")

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed_capture')
def video_feed_capture():
    return Response(gen_frames(purpose='capture'), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_attendance')
@attendance_required
def video_feed_attendance():
    return Response(gen_frames(purpose='attendance'), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
