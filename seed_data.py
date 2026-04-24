import os
import django
import ast
import traceback
import json
import unidecode
import uuid
from datetime import datetime
from django.utils import timezone
from django.db import transaction

# 1. Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # Thay your_project_name bằng tên thư mục chứa settings.py
django.setup()

from travel.models import Attraction, Hotel, Restaurant, Location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def process_line(line):
    # Tách cột bằng khoảng trắng (tab) ở trước
    return line.split('\t')

# Helper để load JSON an toàn
def safe_load_json(data_str):
    if not data_str or data_str.strip() == "":
        return []
    try:
        # Thay gạch dưới thành dấu cách và load
        return json.loads(data_str.replace('_', ' '))
    except json.JSONDecodeError:
        return []

# Xử lí dữ liệu kiểu ngày và id mặc định cho các model con cũng như description
def process_embedded_data(data_list):
    if not data_list: return []
    for item in data_list:
        # 1. Điền ID và các trường bắt buộc (Key phải có dấu gạch dưới chuẩn Model)
        item.setdefault('room_type_id', uuid.uuid4())
        item.setdefault('dish_id', uuid.uuid4())
        item.setdefault('discount_id', uuid.uuid4())
        item.setdefault('comment_id', uuid.uuid4())
        item.setdefault('user_id', "system_seed") # Điền mặc định cho comment
        
        # 2. Xử lý Date (Dành cho Discount)
        for date_field in ['start_date', 'end_date']:
            val = item.get(date_field)
            if val and isinstance(val, str):
                try:
                    item[date_field] = datetime.strptime(val, "%Y-%m-%d").date()
                except:
                    item[date_field] = None
            else:
                item.setdefault(date_field, None)

        # 3. Xử lý DateTime (Dành cho Comment)
        if 'date' not in item:
            item['date'] = timezone.now()

        # 4. Làm sạch dấu gạch dưới CHỈ Ở GIÁ TRỊ (Values)
        # Những trường này thường chứa tiếng Việt có dấu gạch dưới trong file text
        fields_to_clean = ['dish_name', 'type_name', 'title', 'commenter', 'content', 'description']
        for f in fields_to_clean:
            if f in item and isinstance(item[f], str):
                item[f] = item[f].replace('_', ' ')
        
        if 'description' not in item: item['description'] = ""
            
    return data_list



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
                name = parts[0].replace('_', ' ')
                
                # 2. Tạo dictionary dữ liệu cơ bản (Cột 0 -> 14)
                attraction_data = {
                    "name": name,
                    "address": parts[1].replace('_', ' '),
                    "phone_number": parts[2],
                    "description": parts[3].replace('_', ' '),
                    "latitude": float(parts[4]),
                    "longitude": float(parts[5]),
                    "off_weekdays": ast.literal_eval(parts[6]),
                    "off_dates": ast.literal_eval(parts[7]),
                    "active_hours": ast.literal_eval(parts[8]),
                    "price_level": int(parts[9]),
                    "min_price": float(parts[10]),
                    "max_price": float(parts[11]),
                    "review_count": int(parts[12]),
                    "rating": float(parts[13]),
                    "tags": ast.literal_eval(parts[14]),
                }

                # --- XỬ LÝ DỮ LIỆU LỒNG NHAU (Đã giảm số cột) ---
                
                # Cột 15: Giờ là Discounts (Thay vì để trống như trước)
                if len(parts) > 15:
                    raw_discounts = json.loads(parts[15])
                    attraction_data['discounts'] = process_embedded_data(raw_discounts)

                # Cột 16: Giờ là Comments
                if len(parts) > 16:
                    raw_comments = json.loads(parts[16])
                    attraction_data['comments'] = process_embedded_data(raw_comments)

                # 3. Lưu vào Database
                Attraction.objects.create(**attraction_data)
                print(f"✅ Created Attraction: {name}")
                
            except Exception as e:
                print(f"❌ Lỗi tại địa điểm {parts[0] if parts else 'unknown'}: {e}")
                print("-" * 50)
                raise e

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
                
                # 1. Chuẩn bị dữ liệu mặc định (Cột 0 -> 14)
                attraction_defaults = {
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
                    'tags': ast.literal_eval(parts[14]),
                }

                # 2. Xử lý các cột dữ liệu lồng nhau (Đã đôn lên cột 15, 16 giống Hàm 1)
                
                # Cột 15: Discounts
                if len(parts) > 15:
                    raw_discounts = json.loads(parts[15])
                    attraction_defaults['discounts'] = process_embedded_data(raw_discounts)
                
                # Cột 16: Comments
                if len(parts) > 16:
                    raw_comments = json.loads(parts[16])
                    attraction_defaults['comments'] = process_embedded_data(raw_comments)

                # 3. Thực hiện Update hoặc Create
                obj, created = Attraction.objects.update_or_create(
                    name=name,
                    defaults=attraction_defaults
                )
                
                if created:
                    print(f"✅ Tạo mới: {name}")
                else:
                    # Kiểm tra xem có bao nhiêu comment để in log cho đẹp
                    c_count = len(attraction_defaults.get('comments', []))
                    print(f"🔄 Cập nhật: {name} ({c_count} bình luận)")
                
            except Exception as e:
                print(f"❌ Lỗi tại địa điểm {parts[0] if parts else 'unknown'}: {e}")
                print("-" * 50)
                raise e



# ---------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------HOTEL-----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# HÀM 1: XÓA SẠCH RỒI TẠO MỚI (Dùng khi reset data)
def seed_hotels_clear_and_create(file_path):
    # Dọn dẹp bảng Hotel trước khi nạp
    Hotel.objects.all().delete()
    print("--- 🗑️  Đã xóa sạch và bắt đầu nạp mới Hotel 🛏️  ---")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = process_line(line)
            try:
                name = parts[0].replace('_', ' ')
                
                # Tạo dictionary dữ liệu cơ bản
                hotel_data = {
                    "name": name,
                    "address": parts[1].replace('_', ' '),
                    "phone_number": parts[2],
                    "description": parts[3].replace('_', ' '),
                    "latitude": float(parts[4]),
                    "longitude": float(parts[5]),
                    "off_weekdays": ast.literal_eval(parts[6]),
                    "off_dates": ast.literal_eval(parts[7]),
                    "active_hours": ast.literal_eval(parts[8]),
                    "price_level": int(parts[9]),
                    "min_price": float(parts[10]),
                    "max_price": float(parts[11]),
                    "review_count": int(parts[12]),
                    "rating": float(parts[13]),
                    "hotel_type": int(parts[14]), # Trường riêng của Hotel
                }

                # --- XỬ LÝ MODEL CON (ARRAYFIELD) ---
                
                # Cột 15: Room Types (Thay cho Dishes của Restaurant)
                if len(parts) > 15:
                    raw_rooms = json.loads(parts[15])
                    hotel_data['room_types'] = process_embedded_data(raw_rooms)
                
                # Cột 16: Discounts (Kế thừa từ CommonInfo)
                if len(parts) > 16:
                    raw_discounts = json.loads(parts[16])
                    hotel_data['discounts'] = process_embedded_data(raw_discounts)

                # Cột 17: Comments (Kế thừa từ CommonInfo)
                if len(parts) > 17:
                    raw_comments = json.loads(parts[17])
                    hotel_data['comments'] = process_embedded_data(raw_comments)

                # Tạo object và lưu vào MongoDB
                Hotel.objects.create(**hotel_data)

                print(f"✅ Created Hotel: {name} với {len(hotel_data.get('room_types', []))} loại phòng")
            
            except Exception as e:
                print(f"❌ Lỗi tại khách sạn: {parts[0] if parts else 'unknown'}")
                print("-" * 50)
                raise e

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
                
                # 1. Chuẩn bị dữ liệu cơ bản trong defaults
                hotel_defaults = {
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
                    'hotel_type': int(parts[14]),
                }

                # 2. Xử lý các cột dữ liệu lồng nhau (ArrayField) - Giống Hàm 1
                # Cột 15: Room Types
                if len(parts) > 15:
                    raw_rooms = json.loads(parts[15])
                    hotel_defaults['room_types'] = process_embedded_data(raw_rooms)
                
                # Cột 16: Discounts
                if len(parts) > 16:
                    raw_discounts = json.loads(parts[16])
                    hotel_defaults['discounts'] = process_embedded_data(raw_discounts)

                # Cột 17: Comments
                if len(parts) > 17:
                    raw_comments = json.loads(parts[17])
                    hotel_defaults['comments'] = process_embedded_data(raw_comments)

                # 3. Thực hiện Update hoặc Create
                obj, created = Hotel.objects.update_or_create(
                    name=name,
                    defaults=hotel_defaults
                )
                
                status = "✅ Tạo mới" if created else "🔄 Cập nhật"
                room_count = len(hotel_defaults.get('room_types', []))
                print(f"{status}: {name} ({room_count} loại phòng)")

            except Exception as e:
                print(f"❌ Lỗi tại khách sạn {parts[0] if parts else 'unknown'}: {e}")
                print("-" * 50)
                raise e



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
                name = parts[0].replace('_', ' ')
                
                # Tạo dictionary dữ liệu cơ bản
                restaurant_data = {
                    "name": name,
                    "address": parts[1].replace('_', ' '),
                    "phone_number": parts[2],
                    "description": parts[3].replace('_', ' '),
                    "latitude": float(parts[4]),
                    "longitude": float(parts[5]),
                    "off_weekdays": ast.literal_eval(parts[6]),
                    "off_dates": ast.literal_eval(parts[7]),
                    "active_hours": ast.literal_eval(parts[8]),
                    "price_level": int(parts[9]),
                    "min_price": float(parts[10]),
                    "max_price": float(parts[11]),
                    "review_count": int(parts[12]),
                    "rating": float(parts[13]),
                    "cuisine_types": ast.literal_eval(parts[14]),
                }

                # --- XỬ LÝ MODEL CON (ARRAYFIELD) ---
                
                # Cột 15: Dishes (Nếu có)
                if len(parts) > 15:
                    raw_dishes = json.loads(parts[15])
                    restaurant_data['dishes'] = process_embedded_data(raw_dishes)
                
                # Cột 16: Discounts (Nếu có)
                if len(parts) > 16:
                    raw_discounts = json.loads(parts[16])
                    restaurant_data['discounts'] = process_embedded_data(raw_discounts)

                # Cột 17: Comments (Nếu có)
                if len(parts) > 17:
                    raw_comments = json.loads(parts[17]) # BỎ .replace('_', ' ') ở đây
                    restaurant_data['comments'] = process_embedded_data(raw_comments)

                # Tạo object và lưu vào MongoDB
                Restaurant.objects.create(**restaurant_data)

                print(f"✅ Created Restaurant: {name} với {len(restaurant_data.get('dishes', []))} món ăn")
            except Exception as e:
                print(f"❌ Lỗi tại nhà hàng: {parts[0] if parts else 'unknown'}")
                # In ra traceback lỗi cuối cùng rồi văng lỗi để dừng script luôn
                print("-" * 50)
                raise e

# HÀM 2: CẬP NHẬT HOẶC TẠO MỚI (Dùng khi nạp thêm, tránh nặng máy)             
def seed_restaurants_update_or_create(file_path):
    print("--- 🔄 Đang kiểm tra và cập nhật Nhà hàng 🍜 ---")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            parts = process_line(line)
            try:
                name = parts[0].replace('_', ' ')
                
                # 1. Chuẩn bị dữ liệu cơ bản trong defaults
                restaurant_defaults = {
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
                    'cuisine_types': ast.literal_eval(parts[14]),
                }

                # 2. Xử lý các cột dữ liệu lồng nhau (ArrayField) nếu có
                # Cột 15: Dishes
                if len(parts) > 15:
                    raw_dishes = json.loads(parts[15])
                    restaurant_defaults['dishes'] = process_embedded_data(raw_dishes)
                
                # Cột 16: Discounts
                if len(parts) > 16:
                    raw_discounts = json.loads(parts[16])
                    restaurant_defaults['discounts'] = process_embedded_data(raw_discounts)

                # Cột 17: Comments
                if len(parts) > 17:
                    raw_comments = json.loads(parts[17])
                    restaurant_defaults['comments'] = process_embedded_data(raw_comments)

                # 3. Thực hiện Update hoặc Create
                obj, created = Restaurant.objects.update_or_create(
                    name=name,
                    defaults=restaurant_defaults
                )
                
                status = "✅ Tạo mới" if created else "🔄 Cập nhật"
                msg = f"{status}: {name}"
                if 'dishes' in restaurant_defaults:
                    msg += f" ({len(restaurant_defaults['dishes'])} món ăn)"
                print(msg)

            except Exception as e:
                print(f"❌ Lỗi tại nhà hàng: {parts[0] if parts else 'unknown'}")
                print("-" * 50)
                raise e



# ---------------------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------LOCATION----------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------
# HÀM 1: XÓA SẠCH RỒI TẠO MỚI (Dùng khi reset data)
def seed_locations_clear_and_create(file_path):
    """
    Nạp dữ liệu Location từ file TSV (Tab Separated Values)
    Thứ tự cột dự kiến: 
    0: Name | 1: Longitude | 2: Latitude | 3: Is_City | 4: Suggested_Radius
    """
    # 1. Dọn dẹp bảng trước khi nạp
    Location.objects.all().delete()
    print("--- 🗑️  Đã xóa sạch và bắt đầu nạp mới Location 📍 ---")
    
    locations_to_create = []
    count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: 
                continue
            
            # Tách cột bằng dấu Tab
            parts = line.split('\t')
            
            try:
                # Xử lý lấy tên và thay dấu gạch dưới bằng khoảng trắng
                name = parts[0].replace('_', ' ')
                
                # Tạo search_name từ name đã chuẩn hóa (không dấu, viết thường)
                search_name = unidecode.unidecode(name).lower()
                
                # Cấu trúc dữ liệu để lưu vào model
                location_data = {
                    "name": name,
                    "search_name": search_name,
                    "coordinate": {
                        "type": "Point", 
                        "coordinates": [
                            float(parts[1]), # Longitude
                            float(parts[2])  # Latitude
                        ]
                    },
                    # Xử lý boolean cho is_city
                    "is_city": parts[3].strip().lower() in ['true', '1', 't', 'y'],
                    # Bán kính tìm kiếm (như bạn yêu cầu: chỗ đông người thì bán kính nhỏ)
                    "suggested_radius": int(parts[4])
                }

                # Tạo object và lưu vào DB
                Location.objects.create(**location_data)

                print(f"✅ Created Location: {name}")
                
            except Exception as e:
                print(f"❌ Lỗi tại dòng địa điểm: {parts[0] if parts else 'unknown'}")
                print("-" * 50)
                raise e




# Chạy lệnh nhập
if __name__ == "__main__":
    print("🚀 Script đã bắt đầu chạy...")
    attraction_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_attraction.txt')
    hotel_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_hotel.txt')
    restaurant_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_restaurant.txt')
    location_path = os.path.join(BASE_DIR, 'zRaw_data', 'data_location.txt')

    
    # Thay đổi đường dẫn file thực tế của bạn
    # Thêm dữ liệu vào database:
        # 3 loại hình địa điểm:
    # ----------------------------------------------------
    # seed_attractions_clear_and_create(attraction_path)
    # seed_attractions_update_or_create(attraction_path)
    # seed_hotels_clear_and_create(hotel_path)
    # seed_hotels_update_or_create(hotel_path)
    # seed_restaurants_clear_and_create(restaurant_path)
    # seed_restaurants_update_or_create(restaurant_path)
    # ----------------------------------------------------
        # Location:
    seed_locations_clear_and_create(location_path)
    pass
