import os
import django
import ast
import traceback

# 1. Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Thay your_project_name bằng tên thư mục chứa settings.py
django.setup()

from travel.models import Attraction, Hotel, Restaurant
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def process_line(line):
    # Tách cột bằng khoảng trắng trước
    return line.split()



# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------ATTRACTION----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# HÀM 1: XÓA SẠCH RỒI TẠO MỚI (Dùng khi reset data)
def seed_attractions_clear_and_create(file_path):
    # 1. Xóa sạch dữ liệu cũ
    Attraction.objects.all().delete()
    print("--- 🗑️  Đã xóa sạch và bắt đầu nạp mới Attraction 🎡  ---")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = process_line(line)
            try:
                # 2. Xử lý văn bản (thay gạch dưới bằng khoảng trắng)
                name = parts[0].replace('_', ' ')
                address = parts[1].replace('_', ' ')
                description = parts[3].replace('_', ' ')
                
                # 3. Lưu vào Database
                Attraction.objects.create(
                    name=name,
                    address=address,
                    phone_number=parts[2],
                    description=description,
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    off_weekdays=ast.literal_eval(parts[6]),
                    off_dates=ast.literal_eval(parts[7]),
                    active_hours=ast.literal_eval(parts[8]),
                    price_level=int(parts[9]),
                    min_price=float(parts[10]),
                    max_price=float(parts[11]),
                    review_count=int(parts[12]),
                    rating=float(parts[13]),
                    tags=ast.literal_eval(parts[14]) # Cột 14 cho Attraction là danh sách Tags
                )
                print(f"✅ Created Attraction: {name}")
                
            except Exception as e:
                print(f"❌ Lỗi tại địa điểm {parts[0]}: {e}")

# HÀM 2: CẬP NHẬT HOẶC TẠO MỚI (Dùng khi nạp thêm, tránh nặng máy)
def seed_attractions_update_or_create(file_path):
    print("--- 🔄 Đang nhập dữ liệu Attraction 🎡  ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = process_line(line)
            
            try:
                name = parts[0].replace('_', ' ')
                
                # Dùng update_or_create để kiểm tra theo Tên
                obj, created = Attraction.objects.update_or_create(
                    name=name,
                    defaults={
                        'address': parts[1].replace('_', ' '),
                        'phone_number': parts[2],
                        'description': parts[3].replace('_', ' '),
                        'latitude': float(parts[4]),
                        'longitude': float(parts[5]),
                        'off_weekdays': ast.literal_eval(parts[6]),
                        'off_dates': ast.literal_eval(parts[7]),
                        'active_hours': ast.literal_eval(parts[8]),
                        'price_level': int(parts[9]),
                        'min_price': float(parts[10]),
                        'max_price': float(parts[11]),
                        'review_count': int(parts[12]),
                        'rating': float(parts[13]),
                        'tags': ast.literal_eval(parts[14])
                    }
                )
                
                if created:
                    print(f"✅ Tạo mới: {name}")
                else:
                    print(f"🔄 Cập nhật: {name}")
                
            except Exception as e:
                print(f"❌ Lỗi tại {parts[0]}: {e}")
                # print(f"❌ LỖI TẠI: {name}")
                # print(f"Số lượng cột đếm được: {len(parts)}")
                # print(f"Chi tiết kỹ thuật: {traceback.format_exc()}")

    print("--- Hoàn tất ---")



# ---------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------HOTEL-----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# HÀM 1: XÓA SẠCH RỒI TẠO MỚI (Dùng khi reset data)
def seed_hotels_clear_and_create(file_path):
    Hotel.objects.all().delete()
    print("--- 🗑️  Đã xóa sạch và bắt đầu nạp mới Hotel 🛏️  ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = process_line(line)
            try:
                Hotel.objects.create(
                    name=parts[0].replace('_', ' '),
                    address=parts[1].replace('_', ' '),
                    phone_number=parts[2],
                    description=parts[3].replace('_', ' '),
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    off_weekdays=ast.literal_eval(parts[6]),
                    off_dates=ast.literal_eval(parts[7]),
                    active_hours=ast.literal_eval(parts[8]),
                    price_level=int(parts[9]),
                    min_price=float(parts[10]),
                    max_price=float(parts[11]),
                    review_count=int(parts[12]),
                    rating=float(parts[13]),
                    hotel_type=int(parts[14]) # Cột 14 là hotel_type
                )
                print(f"✅ Created Hotel: {parts[0]}")
            except Exception as e:
                print(f"❌ Lỗi tại khách sạn {parts[0]}: {e}")

# HÀM 2: CẬP NHẬT HOẶC TẠO MỚI (Dùng khi nạp thêm, tránh nặng máy)
def seed_hotels_update_or_create(file_path):
    print("--- 🔄 Đang kiểm tra và cập nhật Hotel 🛏️  ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = process_line(line)
            try:
                name = parts[0].replace('_', ' ')
                obj, created = Hotel.objects.update_or_create(
                    name=name,
                    defaults={
                        'address': parts[1].replace('_', ' '),
                        'phone_number': parts[2],
                        'description': parts[3].replace('_', ' '),
                        'latitude': float(parts[4]),
                        'longitude': float(parts[5]),
                        'off_weekdays': ast.literal_eval(parts[6]),
                        'off_dates': ast.literal_eval(parts[7]),
                        'active_hours': ast.literal_eval(parts[8]),
                        'price_level': int(parts[9]),
                        'min_price': float(parts[10]),
                        'max_price': float(parts[11]),
                        'review_count': int(parts[12]),
                        'rating': float(parts[13]),
                        'hotel_type': int(parts[14])
                    }
                )
                print(f"{'✅ Tạo mới' if created else '🔄 Cập nhật'}: {name}")
            except Exception as e:
                print(f"❌ Lỗi tại {parts[0]}: {e}")



# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------RESTAURANT----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# HÀM 1: XÓA SẠCH RỒI TẠO MỚI (Dùng khi reset data)
def seed_restaurants_clear_and_create(file_path):
    # Dọn dẹp bảng Restaurant trước khi nạp
    Restaurant.objects.all().delete()
    print("--- 🗑️  Đã xóa sạch và bắt đầu nạp mới Restaurant 🍜  ---")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = process_line(line)
            try:
                # Xử lý văn bản có dấu gạch dưới
                name = parts[0].replace('_', ' ')
                address = parts[1].replace('_', ' ')
                description = parts[3].replace('_', ' ')
                
                Restaurant.objects.create(
                    name=name,
                    address=address,
                    phone_number=parts[2],
                    description=description,
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    off_weekdays=ast.literal_eval(parts[6]),
                    off_dates=ast.literal_eval(parts[7]),
                    active_hours=ast.literal_eval(parts[8]),
                    price_level=int(parts[9]),
                    min_price=float(parts[10]),
                    max_price=float(parts[11]),
                    review_count=int(parts[12]),
                    rating=float(parts[13]),
                    cuisine_types=ast.literal_eval(parts[14]) # Cột 14 là cuisine_type
                )
                print(f"✅ Created Restaurant: {name}")
            except Exception as e:
                print(f"❌ Lỗi tại nhà hàng {parts[0]}: {e}")

# HÀM 2: CẬP NHẬT HOẶC TẠO MỚI (Dùng khi nạp thêm, tránh nặng máy)             
def seed_restaurants_update_or_create(file_path):
    print("--- 🔄 Đang kiểm tra và cập nhật Nhà hàng 🍜  ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = process_line(line)
            try:
                name = parts[0].replace('_', ' ')
                obj, created = Restaurant.objects.update_or_create(
                    name=name,
                    defaults={
                        'address': parts[1].replace('_', ' '),
                        'phone_number': parts[2],
                        'description': parts[3].replace('_', ' '),
                        'latitude': float(parts[4]),
                        'longitude': float(parts[5]),
                        'off_weekdays': ast.literal_eval(parts[6]),
                        'off_dates': ast.literal_eval(parts[7]),
                        'active_hours': ast.literal_eval(parts[8]),
                        'price_level': int(parts[9]),
                        'min_price': float(parts[10]),
                        'max_price': float(parts[11]),
                        'review_count': int(parts[12]),
                        'rating': float(parts[13]),
                        'cuisine_types': ast.literal_eval(parts[14]) # Cột 14 cho Restaurant
                    }
                )
                print(f"{'✅ Tạo mới' if created else '🔄 Cập nhật'}: {name}")
            except Exception as e:
                print(f"❌ Lỗi tại {parts[0]}: {e}")

# Chạy lệnh nhập
if __name__ == "__main__":
    print("🚀 Script đã bắt đầu chạy...")
    attraction_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_attraction.txt')
    hotel_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_hotel.txt')
    restaurant_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_restaurant.txt')
    
# Lần tới chạy clear tại quên chỉnh off_weekdays rỗng
    # Thay đổi đường dẫn file thực tế của bạn
    seed_attractions_clear_and_create(attraction_path)
    # seed_attractions_update_or_create(attraction_path)
    seed_hotels_clear_and_create(hotel_path)
    # seed_hotels_update_or_create(hotel_path)
    seed_restaurants_clear_and_create(restaurant_path)
    # seed_restaurants_update_or_create(restaurant_path)
    pass