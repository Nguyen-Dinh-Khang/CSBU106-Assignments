## 🚀 Hướng dẫn thiết lập môi trường (Setup)

Làm theo các bước sau để chạy dự án trên máy tính của bạn:

### 1. Clone dự án và truy cập thư mục
```bash
git clone <link-github-cua-ban>
cd CSBU106-Assignments
```

### 2. Tạo môi trường ảo
```bash
# Windows
python -m venv .venv

# macOS/Linux
python3 -m venv .venv
```


### 3. Kích hoạt môi trường ảo
```bash
Windows (PowerShell): .\.venv\Scripts\Activate.ps1
Windows (CMD): .venv\Scripts\activate
macOS/Linux: source .venv/bin/activate
```


### 4. Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```


### 5. Khởi chạy Server
```bash
python manage.py runserver
```

