from flask import Flask, render_template
from config import Config

# Import blueprints
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    
    # Apply configuration
    app.config.from_object(Config)
    
    # Register blueprints (Modular routing)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(attendance_bp)
    
    # Default home route
    @app.route('/')
    def index():
        return render_template('base.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
