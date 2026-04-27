from flask import Blueprint, render_template

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/')
def dashboard():
    return "Student Dashboard (Placeholder)"
