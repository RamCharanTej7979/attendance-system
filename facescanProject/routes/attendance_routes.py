from flask import Blueprint, render_template

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/')
def current_attendance():
    return "Live Attendance Page (Placeholder)"
