# 🔧 Khắc phục lỗi ERR_CONNECTION_REFUSED

## 🚨 Lỗi "localhost đã từ chối kết nối"

### ✅ Giải pháp nhanh:

1. **Chạy script deploy đơn giản:**

   ```bash
   # Chọn 1 trong 3 cách:

   # Cách 1: Đơn giản nhất (không cần Docker)
   python-deploy.bat

   # Cách 2: Docker đơn giản
   simple-deploy.bat

   # Cách 3: Menu tương tác
   quick-deploy.bat  # Chọn option 2 hoặc 3
   ```

## 🌐 Người mạng khác muốn truy cập?

### 🔥 Ngrok (Khuyến nghị):
```bash
# 1. Chạy app trước
python-deploy.bat

# 2. Tải Ngrok: https://ngrok.com/download
# 3. Đăng ký miễn phí: https://ngrok.com/signup
# 4. Setup
ngrok authtoken YOUR_AUTHTOKEN
ngrok http 5000

# 5. Chia sẻ URL: https://abc123.ngrok.io
```

### ⚡ Script tự động:
```bash
internet-access.bat
# Hoặc: quick-deploy.bat (option 9)
```

2. **Kiểm tra ứng dụng đã chạy chưa:**

   ```bash
   # Mở Command Prompt và chạy:
   netstat -an | findstr :5000

   # Nếu thấy ":5000" có nghĩa app đã chạy
   ```

3. **Cho phép mọi người truy cập:**
   ```bash
   # Chạy script firewall (Run as Administrator):
   firewall-config.bat
   # Chọn option 1
   ```

### 🌐 URL để truy cập:

- **Máy bạn:** http://localhost:5000
- **Mạng nội bộ:** http://[IP_ADDRESS]:5000
- **Mobile:** http://[IP_ADDRESS]:5000

### 📱 Tìm IP của bạn:

```bash
ipconfig | findstr "IPv4"
# Hoặc chạy:
quick-deploy.bat  # Option 8
```

### 🔒 Login mặc định:

- **Username:** admin
- **Password:** admin123

### 🛠️ Nếu vẫn lỗi:

1. **Kiểm tra port 5000:**

   ```bash
   netstat -an | findstr :5000
   ```

2. **Tắt Windows Firewall tạm thời** (để test):

   - Windows Settings → Network & Internet → Windows Security → Firewall & network protection → Turn off

3. **Restart lại:**

   ```bash
   quick-deploy.bat  # Option 5 (Stop) rồi deploy lại
   ```

4. **Chạy trực tiếp với Python:**
   ```bash
   python app.py
   ```

### 🎯 Test nhanh:

```bash
# Mở trình duyệt và vào:
http://localhost:5000/health

# Nếu thấy {"status": "healthy"} là OK!
```

---

💡 **Tip:** Dùng `python-deploy.bat` nếu không muốn cài Docker!
