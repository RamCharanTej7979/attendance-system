import sqlite3
import os
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'attendance.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'schema.sql')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        with open(SCHEMA_PATH, 'r') as f:
            cursor.executescript(f.read())
            cursor.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)",
               ("admin", "admin123"))
        conn.commit()
    finally:
        conn.close()

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10) # Added timeout safeguard
    conn.row_factory = sqlite3.Row
    return conn

def verify_admin(username, password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (username, password))
        row = cursor.fetchone()
        if row:
            return True
        return False
    finally:
        conn.close()

def add_student(name, roll_number, face_encoding):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Enforce float64 type consistently for binary compatibility
        enforce_enc = np.array(face_encoding, dtype=np.float64)
        encoding_blob = enforce_enc.tobytes()
        
        cursor.execute("INSERT INTO students (name, roll_number, face_encoding) VALUES (?, ?, ?)", 
                       (name, roll_number, encoding_blob))
        student_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO summary (student_id) VALUES (?)", (student_id,))
        conn.commit()
        return True, "Student added successfully"
    except sqlite3.IntegrityError:
        return False, "Roll number already exists"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_all_students_encodings():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, roll_number, name, face_encoding FROM students")
        rows = cursor.fetchall()
        
        students = []
        for row in rows:
            encoding = np.frombuffer(row['face_encoding'], dtype=np.float64)
            students.append({
                'id': row['id'],
                'roll_number': row['roll_number'],
                'name': row['name'],
                'encoding': encoding
            })
        return students
    finally:
        conn.close()

def get_student_by_roll(roll_number):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def get_all_students():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        rows = cursor.fetchall()
        
        students = []
        for r in rows:
            d = dict(r)
            d.pop('face_encoding', None)
            students.append(d)
        return students
    finally:
        conn.close()

def mark_attendance(student_id, date, time):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Initial check to avoid IntegrityError exceptions triggering globally
        cursor.execute("SELECT id FROM attendance WHERE student_id = ? AND date = ?", (student_id, date))
        if cursor.fetchone():
            return False, "Already marked"

        cursor.execute("INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, 'Present')", 
                       (student_id, date, time))
        
        # Safely count present days overall to avoid sync issues
        cursor.execute("SELECT COUNT(*) as count FROM attendance WHERE student_id = ?", (student_id,))
        present_count = cursor.fetchone()['count']
        
        # Assume 25 working days base, clamped at 100% just in case
        percentage = min((present_count / 25.0) * 100, 100.0)
        
        cursor.execute("UPDATE summary SET present_days = ?, percentage = ? WHERE student_id = ?", 
                       (present_count, percentage, student_id))
        
        conn.commit()
        return True, "Attendance marked"
    except sqlite3.IntegrityError:
        return False, "Already marked"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_attendance_records():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT attendance.*, students.name, students.roll_number 
            FROM attendance 
            JOIN students ON attendance.student_id = students.id
            ORDER BY attendance.date DESC, attendance.time DESC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_student_attendance(student_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC", (student_id,))
        rows = cursor.fetchall()
        
        cursor.execute("SELECT * FROM summary WHERE student_id = ?", (student_id,))
        summary = cursor.fetchone()
        
        return [dict(row) for row in rows], dict(summary) if summary else None
    finally:
        conn.close()

def delete_student(student_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Check if student actually exists
        cursor.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        if not cursor.fetchone():
            return False, "Student not found in the database."

        # 2. Delete related records safely (Cascading from dependents to core)
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM summary WHERE student_id = ?", (student_id,))
        
        # 3. Delete the primary record
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        
        # 4. Commit safely
        conn.commit()
        return True, "Student and all related data deleted permanently."
        
    except Exception as e:
        return False, f"Database error occurred: {str(e)}"
    finally:
        conn.close()

def save_unknown_face(image_path, timestamp):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO unknown_faces (image_path, timestamp) VALUES (?, ?)", (image_path, timestamp))
        conn.commit()
    finally:
        conn.close()

def get_unknown_faces():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM unknown_faces ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
