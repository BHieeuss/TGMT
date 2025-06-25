# Hướng dẫn Copilot cho Ứng dụng Điểm danh Khuôn mặt

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Mô tả dự án

Đây là ứng dụng web điểm danh sinh viên sử dụng công nghệ nhận diện khuôn mặt, được phát triển bằng Python Flask.

## Cấu trúc dự án

- `app.py`: File chính chạy ứng dụng Flask
- `models/`: Chứa các model database (SQLite)
- `routes/`: Chứa các route/endpoint API
- `templates/`: Chứa các template HTML
- `static/`: Chứa CSS, JavaScript, hình ảnh
- `uploads/`: Thư mục lưu ảnh sinh viên
- `exports/`: Thư mục xuất file báo cáo Excel

## Công nghệ sử dụng

- Backend: Python Flask, SQLite
- Frontend: HTML5, CSS3, JavaScript, Bootstrap
- AI/ML: OpenCV, face_recognition
- Export: pandas, openpyxl

## Chức năng chính

1. Quản lý lớp học và sinh viên
2. Tạo môn học và ca điểm danh
3. Điểm danh bằng nhận diện khuôn mặt
4. Xuất báo cáo Excel

## Lưu ý khi code

- Sử dụng Bootstrap cho UI responsive
- Implement proper error handling
- Tối ưu hóa performance cho face recognition
- Đảm bảo security cho file upload
