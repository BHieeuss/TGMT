import os
import pickle
import numpy as np
import face_recognition
from PIL import Image
import cv2
import sqlite3
from datetime import datetime

class FaceRecognitionModel:
    def __init__(self, model_path="models/face_encodings.pkl"):
        self.model_path = model_path
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.load_model()
    
    def load_model(self):
        """Load trained model from file"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_names = data['names']
                    self.known_face_ids = data['ids']
                print(f"Model loaded: {len(self.known_face_encodings)} faces")
            except Exception as e:
                print(f"Error loading model: {e}")
                self.known_face_encodings = []
                self.known_face_names = []
                self.known_face_ids = []
    
    def save_model(self):
        """Save trained model to file"""
        try:
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names,
                'ids': self.known_face_ids
            }
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(data, f)
            print(f"Model saved: {len(self.known_face_encodings)} faces")
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def get_student_info(self, student_id):
        """Get student info from database"""
        try:
            conn = sqlite3.connect('attendance_system.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT student_id, full_name, class_id 
                FROM students 
                WHERE student_id = ?
            """, (student_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'student_id': result[0],
                    'full_name': result[1],
                    'class_id': result[2]
                }
            return None
        except Exception as e:
            print(f"Error getting student info: {e}")
            return None
    
    def train_from_folder(self, folder_path="uploads/faces"):
        """Train model from student face images"""
        print("Starting face recognition training...")
        
        new_encodings = []
        new_names = []
        new_ids = []
        
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return False
        
        student_folders = [f for f in os.listdir(folder_path) 
                          if os.path.isdir(os.path.join(folder_path, f))]
        
        total_students = len(student_folders)
        processed_students = 0
        
        print(f"Found {total_students} student folders")
        
        for student_id in student_folders:
            student_folder = os.path.join(folder_path, student_id)
            student_info = self.get_student_info(student_id)
            
            if not student_info:
                print(f"Student {student_id} not found in database")
                continue
            
            student_name = student_info['full_name']
            image_files = [f for f in os.listdir(student_folder) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if not image_files:
                print(f"No images found for student {student_id}")
                continue
            
            print(f"Processing {student_id} - {student_name} ({len(image_files)} images)")
            
            student_encodings = []
            
            for image_file in image_files:
                image_path = os.path.join(student_folder, image_file)
                
                try:
                    # Load image
                    image = face_recognition.load_image_file(image_path)
                    
                    # Get face encodings
                    face_encodings = face_recognition.face_encodings(image)
                    
                    if len(face_encodings) > 0:
                        # Use the first face found
                        encoding = face_encodings[0]
                        student_encodings.append(encoding)
                    else:
                        print(f"No face found in {image_file}")
                        
                except Exception as e:
                    print(f"Error processing {image_file}: {e}")
            
            if student_encodings:
                # Average all encodings for this student
                avg_encoding = np.mean(student_encodings, axis=0)
                
                new_encodings.append(avg_encoding)
                new_names.append(student_name)
                new_ids.append(student_id)
                
                print(f"✓ Added {student_name} with {len(student_encodings)} face encodings")
            
            processed_students += 1
            print(f"Progress: {processed_students}/{total_students} students")
        
        # Update model data
        self.known_face_encodings = new_encodings
        self.known_face_names = new_names
        self.known_face_ids = new_ids
        
        # Save model
        if self.save_model():
            print(f"✓ Training completed! Model trained with {len(new_encodings)} students")
            return {
                'success': True,
                'total_students': len(new_encodings),
                'message': f'Model trained successfully with {len(new_encodings)} students'
            }
        else:
            print("✗ Failed to save model")
            return {
                'success': False,
                'message': 'Failed to save trained model'
            }
    
    def recognize_face(self, image_data):
        """Recognize face from base64 image data"""
        try:
            # Convert base64 to image
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            import base64
            image_bytes = base64.b64decode(image_data)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find faces in the image
            face_locations = face_recognition.face_locations(image_rgb)
            face_encodings = face_recognition.face_encodings(image_rgb, face_locations)
            
            results = []
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Compare with known faces
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                name = "Unknown"
                student_id = None
                confidence = 0
                
                if True in matches:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        student_id = self.known_face_ids[best_match_index]
                        confidence = 1 - face_distances[best_match_index]
                
                results.append({
                    'name': name,
                    'student_id': student_id,
                    'confidence': float(confidence),
                    'location': {
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left
                    }
                })
            
            return {
                'success': True,
                'face_count': len(results),
                'faces': results
            }
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return {
                'success': False,
                'error': str(e),
                'face_count': 0,
                'faces': []
            }
    
    def get_model_info(self):
        """Get information about the current model"""
        return {
            'total_faces': len(self.known_face_encodings),
            'students': list(zip(self.known_face_ids, self.known_face_names)),
            'model_exists': os.path.exists(self.model_path),
            'model_path': self.model_path
        }
    
    def add_student_to_model(self, student_id):
        """Add a specific student to the model"""
        student_folder = f"uploads/faces/{student_id}"
        
        if not os.path.exists(student_folder):
            return {
                'success': False,
                'message': f'No face data found for student {student_id}'
            }
        
        student_info = self.get_student_info(student_id)
        if not student_info:
            return {
                'success': False,
                'message': f'Student {student_id} not found in database'
            }
        
        # Remove existing data for this student
        indices_to_remove = [i for i, sid in enumerate(self.known_face_ids) if sid == student_id]
        for i in reversed(indices_to_remove):
            del self.known_face_encodings[i]
            del self.known_face_names[i]
            del self.known_face_ids[i]
        
        # Add new data
        student_name = student_info['full_name']
        image_files = [f for f in os.listdir(student_folder) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        student_encodings = []
        
        for image_file in image_files:
            image_path = os.path.join(student_folder, image_file)
            
            try:
                image = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if len(face_encodings) > 0:
                    student_encodings.append(face_encodings[0])
                    
            except Exception as e:
                print(f"Error processing {image_file}: {e}")
        
        if student_encodings:
            # Average all encodings
            avg_encoding = np.mean(student_encodings, axis=0)
            
            self.known_face_encodings.append(avg_encoding)
            self.known_face_names.append(student_name)
            self.known_face_ids.append(student_id)
            
            if self.save_model():
                return {
                    'success': True,
                    'message': f'Added {student_name} to model with {len(student_encodings)} face encodings'
                }
        
        return {
            'success': False,
            'message': f'No valid face encodings found for student {student_id}'
        }

# Global model instance
face_model = FaceRecognitionModel()
