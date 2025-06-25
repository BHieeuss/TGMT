from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import os
import sqlite3
from datetime import datetime
import cv2
import face_recognition
import numpy as np
from PIL import Image
import base64
import io
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXPORT_FOLDER'] = 'exports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and export directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Import routes
from routes.auth import auth_bp
from routes.classes import classes_bp
from routes.students import students_bp
from routes.subjects import subjects_bp
from routes.attendance import attendance_bp
from routes.reports import reports_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(classes_bp, url_prefix='/classes')
app.register_blueprint(students_bp, url_prefix='/students')
app.register_blueprint(subjects_bp, url_prefix='/subjects')
app.register_blueprint(attendance_bp, url_prefix='/attendance')
app.register_blueprint(reports_bp, url_prefix='/reports')

@app.route('/')
def index():
    """Dashboard trang chủ"""
    from models.database import get_dashboard_stats
    stats = get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/camera')
def camera():
    """Trang điểm danh bằng camera"""
    return render_template('camera.html')

if __name__ == '__main__':
    # Khởi tạo database
    from models.database import init_database
    init_database()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
