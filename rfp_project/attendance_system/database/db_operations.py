import pickle
from datetime import date
from database.db_connection import get_db_connection
from config import Config

def add_student(name, roll_no, face_encoding):
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        encoding_bytes = pickle.dumps(face_encoding)
        # Insert student
        cursor.execute("INSERT INTO students (name, roll_no, face_encoding) VALUES (%s, %s, %s)",
                       (name, roll_no, encoding_bytes))
        student_id = cursor.lastrowid
        
        # Initialize summary
        cursor.execute("INSERT INTO summary (student_id, present_days, absent_days, percentage) VALUES (%s, 0, %s, 0.0)",
                       (student_id, Config.TOTAL_WORKING_DAYS))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding student: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_all_student_encodings_with_stats():
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = '''
        SELECT s.id, s.roll_no, s.name, s.face_encoding, sum_m.percentage 
        FROM students s
        LEFT JOIN summary sum_m ON s.id = sum_m.student_id
        '''
        cursor.execute(query)
        records = cursor.fetchall()
        for rec in records:
            rec['face_encoding'] = pickle.loads(rec['face_encoding'])
        return records
    except Exception as e:
        print(f"Error fetching encodings: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_all_students_summary():
    """For admin 'View Students' / 'Attendance Summary' UI"""
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = '''
        SELECT s.id, s.roll_no, s.name, sum_m.present_days, sum_m.absent_days, sum_m.percentage 
        FROM students s
        LEFT JOIN summary sum_m ON s.id = sum_m.student_id
        ORDER BY s.roll_no ASC
        '''
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching summary details: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_student_by_roll(roll_no):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE roll_no = %s", (roll_no,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching student: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_student_dashboard_data(roll_no):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        query = '''
        SELECT 
            s.name, 
            s.roll_no, 
            COUNT(a.id) as present_days,
            (%s - COUNT(a.id)) as absent_days,
            (COUNT(a.id) / %s) * 100 as percentage
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.status = 'Present'
        WHERE s.roll_no = %s
        GROUP BY s.id
        '''
        cursor.execute(query, (Config.TOTAL_WORKING_DAYS, Config.TOTAL_WORKING_DAYS, roll_no))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def mark_attendance_db(student_id, mark_date=None):
    if mark_date is None:
        mark_date = date.today()
    
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # Prevent duplicate attendance using UNIQUE constraint try-except
        cursor.execute("INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, 'Present')",
                       (student_id, mark_date))
        
        # If success, update summary
        cursor.execute("UPDATE summary SET present_days = present_days + 1, absent_days = %s - (present_days + 1) WHERE student_id = %s",
                       (Config.TOTAL_WORKING_DAYS, student_id))
        
        # Update percentage dynamically
        cursor.execute("UPDATE summary SET percentage = (present_days / %s) * 100 WHERE student_id = %s",
                       (Config.TOTAL_WORKING_DAYS, student_id))
                       
        conn.commit()
        return True
    # IntegrityError explicitly handles the duplicate insertions (since UNIQUE key covers student_id, date)
    except Exception as e:
        # Expected conflict on duplicates.
        return False
    finally:
        cursor.close()
        conn.close()

def log_unknown_face(image_path):
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO unknown_faces (image_path) VALUES (%s)", (image_path,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving unknown face: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
