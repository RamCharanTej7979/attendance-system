from datetime import date
from database.db_connection import get_db_connection

def mark_end_of_day_absentees():
    """
    Checks the attendance table for today. If any student from the students table
    is not present in today's attendance records, marks them as 'Absent'.
    """
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        today = date.today()
        
        # Insert absent records for all students not in attendance today
        query = '''
        INSERT INTO attendance (student_id, date, status)
        SELECT id, %s, 'Absent'
        FROM students 
        WHERE id NOT IN (
            SELECT student_id FROM attendance WHERE date = %s
        )
        '''
        cursor.execute(query, (today, today))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error marking EOD absentees: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
