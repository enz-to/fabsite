from flask import Flask, render_template, request, jsonify, send_file
import cv2
from deepface import DeepFace
import os
import numpy as np
from datetime import datetime
import json
import pandas as pd

app = Flask(__name__)

# Initialize storage directories
if not os.path.exists('static/faces'):
    os.makedirs('static/faces')
if not os.path.exists('static/attendance'):
    os.makedirs('static/attendance')
if not os.path.exists('static/reports'):
    os.makedirs('static/reports')

# Load student data
def load_students():
    try:
        with open('students.json', 'r') as f:
            return json.load(f)
    except:
        return {}

# Save student data
def save_students(data):
    with open('students.json', 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    students = load_students()
    return render_template('index.html', students=students)

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        student_id = request.form['student_id']
        name = request.form['name']
        course = request.form['course']
        
        # Get image data from the form
        image_data = request.form.get('image')
        if not image_data:
            return jsonify({
                'status': 'error',
                'message': 'No image data received'
            })

        # Convert base64 image to file
        import base64
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Create directory if not exists
        os.makedirs('static/faces', exist_ok=True)
        
        # Save face image
        image_path = f'static/faces/{student_id}.jpg'
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        # Update student database
        students = load_students()
        students[student_id] = {
            'name': name,
            'course': course,
            'image_path': image_path,
            'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_students(students)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/view_students')
def view_students():
    students = load_students()
    return render_template('view_students.html', students=students)

@app.route('/generate_report')
def generate_report():
    try:
        # Get all attendance files
        attendance_dir = 'static/attendance'
        all_attendance = {}
        
        for filename in os.listdir(attendance_dir):
            if filename.endswith('.json'):
                date = filename.split('.')[0]
                with open(os.path.join(attendance_dir, filename), 'r') as f:
                    all_attendance[date] = json.load(f)
        
        # Create report DataFrame
        report_data = []
        students = load_students()
        
        for date, attendance in all_attendance.items():
            for student_id, data in attendance.items():
                report_data.append({
                    'Date': date,
                    'Student ID': student_id,
                    'Name': data['name'],
                    'Time': data['time'],
                    'Course': students.get(student_id, {}).get('course', 'N/A')
                })
        
        if not report_data:
            return jsonify({
                'status': 'error',
                'message': 'No attendance records found'
            })
        
        df = pd.DataFrame(report_data)
        report_path = f'static/reports/attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        df.to_excel(report_path, index=False)
        
        return send_file(report_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/scan_face', methods=['POST'])
def scan_face():
    try:
        image_data = request.json['image']
        import base64
        img_data = base64.b64decode(image_data.split(',')[1])
        temp_path = 'static/temp.jpg'
        with open(temp_path, 'wb') as f:
            f.write(img_data)

        students = load_students()
        
        # Improve face detection accuracy
        backends = ['opencv', 'ssd', 'dlib', 'mtcnn']
        for student_id, student_info in students.items():
            for backend in backends:
                try:
                    result = DeepFace.verify(
                        img1_path=temp_path,
                        img2_path=student_info['image_path'],
                        detector_backend=backend,
                        model_name='VGG-Face',
                        distance_metric='cosine',
                        enforce_detection=True
                    )
                    
                    if result['verified'] and result['distance'] < 0.3:  # Stricter threshold
                        # Record attendance
                        attendance_file = f"static/attendance/{datetime.now().strftime('%Y-%m-%d')}.json"
                        try:
                            with open(attendance_file, 'r') as f:
                                attendance = json.load(f)
                        except:
                            attendance = {}
                        
                        # Check if already marked attendance in last 30 minutes
                        current_time = datetime.now()
                        if student_id in attendance:
                            last_time = datetime.strptime(attendance[student_id]['time'], '%H:%M:%S')
                            last_time = current_time.replace(hour=last_time.hour, minute=last_time.minute, second=last_time.second)
                            if (current_time - last_time).total_seconds() < 1800:  # 30 minutes
                                return jsonify({
                                    'status': 'error',
                                    'message': f'Attendance already marked for {student_info["name"]}'
                                })
                        
                        attendance[student_id] = {
                            'name': student_info['name'],
                            'time': current_time.strftime('%H:%M:%S'),
                            'course': student_info.get('course', 'N/A')
                        }
                        
                        with open(attendance_file, 'w') as f:
                            json.dump(attendance, f, indent=4)
                        
                        return jsonify({
                            'status': 'success',
                            'student': student_info['name']
                        })
                except Exception as e:
                    continue
        
        return jsonify({
            'status': 'error',
            'message': 'No matching student found'
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/start_scanning')
def start_scanning():
    return render_template('scanner.html')

if __name__ == '__main__':
    app.run(debug=True)