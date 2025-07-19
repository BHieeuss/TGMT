# 🌐 Cách cho người mạng khác truy cập website

## 🚀 3 cách đơn giản:

### 1. 🔥 Ngrok (Khuyến nghị - Miễn phí)

```bash
# Bước 1: Chạy app 
python-deploy.bat

# Bước 2: Tải Ngrok
# Tải từ: https://ngrok.com/download
# Giải nén ngrok.exe vào thư mục project

# Bước 3: Đăng ký miễn phí
# Vào: https://ngrok.com/signup
# Copy authtoken từ dashboard

# Bước 4: Setup
ngrok authtoken YOUR_AUTHTOKEN

# Bước 5: Tạo tunnel
ngrok http 5000

# Kết quả: https://abc123.ngrok.io
```

### 2. 🎯 Script tự động

```bash
# Chạy script hỗ trợ
internet-access.bat

# Hoặc từ menu chính
quick-deploy.bat  # Chọn option 9
```

### 3. ⚡ LocalTunnel (Nhanh)

```bash
# Cài Node.js từ: https://nodejs.org/
npm install -g localtunnel

# Chạy app trước
python-deploy.bat

# Tạo tunnel  
lt --port 5000 --subdomain tgmt-attendance

# Kết quả: https://tgmt-attendance.loca.lt
```

## 📱 Chia sẻ với người khác:

1. **Chạy app:** `python-deploy.bat`
2. **Tạo tunnel:** `ngrok http 5000`  
3. **Copy URL:** `https://abc123.ngrok.io`
4. **Chia sẻ:**
   - URL: https://abc123.ngrok.io
   - Username: admin
   - Password: admin123

## ⚠️ Lưu ý:

- ✅ Giữ cửa sổ ngrok/tunnel mở
- ✅ Đổi password mặc định cho bảo mật
- ✅ Chỉ chia sẻ với người tin tưởng
- ✅ Tắt tunnel khi không dùng

## 🔧 Troubleshooting:

```bash
# App không chạy?
netstat -an | findstr :5000

# Ngrok lỗi?
ngrok --version
ngrok authtoken YOUR_TOKEN

# LocalTunnel lỗi?
node --version
npm --version
```

---

💡 **Tip:** Dùng `internet-access.bat` để có hướng dẫn tương tác!
