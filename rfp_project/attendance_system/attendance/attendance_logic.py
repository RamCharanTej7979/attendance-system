from database.db_connection import get_connection
from database.db_operations import fetch_all_students
from attendance.summary import update_attendance_summary
from utils.logger import app_logger
from datetime import date

def process_end_of_day():
    """
    Called at the end of the day or closing of the app.
    Marks all students as Absent if they were not marked Present today,
    then updates the summary table for all students.
    """
    conn = get_connection()
    today = date.today()
    
    if not conn:
        return
        
    try:
        cursor = conn.cursor()
        _, students = fetch_all_students()
        
        for student in students:
            student_id = student['id']
            # Try to insert Absent. It will fail silently (IntegrityError) if the student is already marked Present (or Absent) today
            try:
                query = "INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)"
                cursor.execute(query, (student_id, today, 'Absent'))
                app_logger.info(f"Auto-marked student {student_id} as Absent for {today}")
            except Exception:
                # Already a record exists for today
                pass
                
        conn.commit()
        app_logger.info(f"End of day absent marking completed for {today}")
        
    except Exception as e:
        app_logger.error(f"Error in end-of-day processing: {e}")
    finally:
        conn.close()
        
    # Recompute summary for all students
    update_attendance_summary()
