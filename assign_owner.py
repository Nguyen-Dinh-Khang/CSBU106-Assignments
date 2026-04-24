import os
import django
import traceback

# --- CẤU HÌNH DJANGO MÔI TRƯỜNG ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()


from travel.models import Restaurant, Hotel, Attraction, User 
from django.db import transaction


TYPE_MAPPING = {
    'ATTRACTION': (Attraction, 'ATTRACTION'),
    'HOTEL': (Hotel, 'HOTEL'),
    'RESTAURANT': (Restaurant, 'RESTAURANT'),
}

def update_owner_standalone(user_id, place_id, place_type):
    try:
        place_type = place_type.upper()
        if place_type not in TYPE_MAPPING:
            print(f"❌ Loại {place_type} không hợp lệ.")
            return

        # 1. Tìm User
        user = User.objects.filter(id=user_id).first()
        if not user:
            print(f"❌ User ID {user_id} không tồn tại.")
            return

        # 2. Tìm Model và Địa điểm
        ModelClass, target_type = TYPE_MAPPING[place_type]
        place = ModelClass.objects.filter(id=place_id).first()
        if not place:
            print(f"❌ Địa điểm {place_id} ({place_type}) không tồn tại.")
            return

        # 3. Thực hiện cập nhật bằng Transaction
        with transaction.atomic():
            place.owner = user
            place.save()

            user.role = 'OWNER'
            user.type_location = target_type
            user.save(update_fields=['role', 'type_location'])

        print(f"✅ THÀNH CÔNG: Đã gán '{user.username}' làm chủ '{place.name}'.")

    except Exception:
        print(f"❌ LỖI KHI GÁN OWNER:")
        print(traceback.format_exc())

# --- CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    # Ví dụ: Gán User ID 2 làm chủ Attraction ID 49
    update_owner_standalone(2, 49, 'Attraction')