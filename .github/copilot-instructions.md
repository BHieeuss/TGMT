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

## ⚙️ Quy tắc lập trình

### ✅ Phải:

- Viết mã **sạch**, dễ đọc, dễ bảo trì.
- Tái sử dụng component/helper đã có.
- Dùng **Eloquent** hiệu quả, tránh query thừa.
- Đọc kỹ các code đã xây dựng truớc khi thêm mới hoặc sửa đổi.
- Dữ liệu đầu ra cần xử lý định dạng rõ ràng (tiền tệ, ngày giờ).
- Phân trang, tìm kiếm, sắp xếp hoạt động tốt.
- Dùng `route()`, `asset()`, `url()` thay vì hard-code.
- Tách biệt CSS và JS ra file riêng, không inline.
- Sử dụng Bootstrap 5 classes hợp lý hạn chế dùng css thuần nếu không cần thiết.
- Đặt tên Class phù hợp theo chuẩn không đặt bừa bãi.
- CSS các phần cần đồng bộ với nhau không rời rạc.
- CSS và JS không được viết cùng 1 file html nếu không cần thiết.
- Viết File test, test xong phải xóa đi.
- Các thông báo sử dụng Extention SweetAlert2, không dùng alert().
- Comment phải chia ra từng mục rõ ràng. Ví dụ Header, Footer, Main Content, Sidebar, v.v.

### ❌ Không được:

- Không viết **code lộn xộn**, không theo chuẩn.
- Không viết Comment không rõ ràng, không cần thiết.
- Không viết **code lặp lại** (tuân theo nguyên tắc **DRY**).
- Không viết **query SQL thô** trong controller.
- Không để **logic xử lý trong view**.
- Không dùng **inline style** CSS.
- Không dùng **Bootstrap 3 hoặc 4**.
- Không bỏ qua bước **validate dữ liệu đầu vào**.

---

## 🧠 Gợi ý cho Copilot

- Khi viết view, ưu tiên class Bootstrap 5 hợp lý như: `row`, `col-md-6`, `form-control`, `table`, `btn btn-primary`, v.v.
- Khi viết controller, chia nhỏ hàm nếu quá dài.
- Dùng **Route Model Binding** khi có thể.
- Logic xử lý nên đặt ở **Service**, **Repository** hoặc **Helper**, không nhét vào Controller hay View.

---
