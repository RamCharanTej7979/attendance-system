import cv2
import time
import numpy as np
from database.db_operations import fetch_all_students, fetch_student_summary
from face_recognition_module.face_detector import detect_faces
from face_recognition_module.face_encoder import encode_faces
from face_recognition_module.face_matcher import match_face
from attendance.mark_attendance import mark_student_present
from attendance.attendance_logic import process_end_of_day
from unknown_faces.save_unknown import log_unknown_face
from config import MIN_ATTENDANCE_PERCENTAGE
from utils.logger import app_logger

def main():
    app_logger.info("Initializing Face Recognition Attendance System...")
    
    # Load known faces from database
    known_encodings, known_students = fetch_all_students()
    
    if not known_students:
        app_logger.warning("No students found in the database. Please register students first.")
    else:
        app_logger.info(f"Loaded {len(known_students)} known students.")

    # Prevent spamming unknown face logs (10-second cooldown per unique unknown detection burst)
    last_unknown_log_time = 0
    UNKNOWN_COOLDOWN = 5

    # Start webcam
    video_capture = cv2.VideoCapture(0)
    app_logger.info("Webcam started. Press 'q' to quit and process end of day attendance.")

    try:
        while True:
            ret, frame = video_capture.read()
            if not ret:
                app_logger.error("Failed to grab frame from webcam. Exiting...")
                break
                
            # Resize frame to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert image from BGR color (OpenCV) to RGB color (face_recognition)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Find all face locations and encodings in the current frame
            face_locations = detect_faces(rgb_small_frame)
            face_encodings = encode_faces(rgb_small_frame, face_locations)

            # Loop through each face found in the frame
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # See if the face is a match for the known faces
                match_idx = match_face(face_encoding, known_encodings)
                
                name = "Unknown Face Detected"
                roll_no = ""
                warning = ""
                percentage = 0.0
                box_color = (0, 0, 255) # Red for unknown
                is_known = False

                if match_idx != -1:
                    student = known_students[match_idx]
                    student_id = student['id']
                    name = student['name']
                    roll_no = student['roll_no']
                    is_known = True
                    box_color = (0, 255, 0) # Green for known

                    # Mark present
                    marked_newly = mark_student_present(student_id)
                    if marked_newly:
                        # Draw a quick visual cue or log it. Handled inside mark_attendance
                        pass

                    # Fetch Summary for display
                    summary = fetch_student_summary(student_id)
                    if summary:
                        percentage = float(summary['percentage'])
                        if percentage < MIN_ATTENDANCE_PERCENTAGE:
                            warning = "Low Attendance!"
                            box_color = (0, 165, 255) # Orange for warning
                else:
                    # Handle Unknown Face
                    current_time = time.time()
                    if current_time - last_unknown_log_time > UNKNOWN_COOLDOWN:
                        # Log it
                        # Convert to RGB since log_unknown_face expects it, or pass the full frame which is BGR 
                        # Wait, log_unknown_face converts RGB->BGR. So let's pass a fresh RGB copy of the full frame.
                        full_rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        log_unknown_face(full_rgb_frame, (top, right, bottom, left))
                        last_unknown_log_time = current_time

                # Draw bounding box
                cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
                
                # Draw Label
                font = cv2.FONT_HERSHEY_DUPLEX
                
                if is_known:
                    # Draw a filled rectangle behind the text
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom + 40), box_color, cv2.FILLED)
                    cv2.putText(frame, f"{name} ({roll_no})", (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
                    cv2.putText(frame, f"Attend: {percentage:.1f}%", (left + 6, bottom + 15), font, 0.5, (255, 255, 255), 1)
                    if warning:
                        cv2.putText(frame, warning, (left + 6, bottom + 35), font, 0.5, (0, 0, 255), 1)
                else:
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), box_color, cv2.FILLED)
                    cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

            # Display the resulting image
            cv2.imshow('Face Recognition Attendance System', frame)

            # Hit 'q' on the keyboard to quit!
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        app_logger.error(f"An error occurred in main loop: {e}")
    finally:
        # Release handle to the webcam
        video_capture.release()
        cv2.destroyAllWindows()
        
        # End of day processing (mark absentees)
        app_logger.info("Executing End-of-Day Processing...")
        process_end_of_day()
        app_logger.info("System Shut Down successfully.")

if __name__ == '__main__':
    main()
