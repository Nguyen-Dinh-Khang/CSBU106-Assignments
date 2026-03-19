from djongo import models
from django.conf import settings
import uuid

# --- Cấu trúc Nhúng (Embedded Models) ---

# --- Menu quán ăn ----------------------------------------------------------------------------------------------------------------
class Dish(models.Model):
    dish_id = models.CharField(max_length=100, default=uuid.uuid4, editable=False)
    dish_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    class Meta:
        abstract = True # Dùng để nhúng, không tạo bảng riêng

class Menu(models.Model):
    menu_name = models.CharField(max_length=100)
    dishes = models.ArrayField(model_container=Dish, blank=True, null=True) # Danh sách món ăn nằm trong Menu

    class Meta:
        abstract = True

# --- Giá phòng khác sạn ----------------------------------------------------------------------------------------------------------
class RoomTypePrice(models.Model):
    room_type_id = models.CharField(max_length=100, default=uuid.uuid4, editable=False)
    type_name = models.CharField(max_length=100) # VD: Deluxe, Standard
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    class Meta:
        abstract = True

class RoomPrice(models.Model):
    room_types = models.ArrayField(model_container=RoomTypePrice, blank=True, null=True)

    class Meta:
        abstract = True

# --- Giảm giá --------------------------------------------------------------------------------------------------------------------
class Discount(models.Model):
    discount_id = models.CharField(max_length=100, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200) # Tên chương trình
    percent = models.IntegerField()          # Con số % giảm giá (VD: 10, 20, 50)
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    # Ngày hiệu lực
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        abstract = True

# --- Comment ---------------------------------------------------------------------------------------------------------------------
class Comment(models.Model):
    user_id = models.CharField(max_length=50)
    commenter = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

# ---------------------------------------------------------------------------------------------------------------------------------
# --- Model Chính (Main Document) -------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------------------
# --- Abstract Model để đỡ phải gõ lại các trường chung ---
class CommonInfo(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    # Chủ sở hữu
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'OWNER'}, # Chỉ hiện danh sách các Owner trong Admin
        related_name="owned_%(class)s",     # Tạo tên ngược: user.owned_restaurant, user.owned_hotel...
        null=True,
        blank=True
    )

    # Tọa độ
    latitude = models.FloatField()  # Trong khoảng [-90, 90] 
    longitude = models.FloatField() # Trong khoảng [-180, 180]
    location = models.JSONField(default=dict) # Tự động lưu

    # Thời gian hoạt động
    off_weekdays = models.JSONField(default=list) # [1, 7] (1: chủ nhật, 7: thứ 7)
    off_dates = models.JSONField(default=list)    # ["01-01", "30-04", "01-05"] (ngày-tháng)
    active_hours = models.JSONField(default=list) # [1, 3] (0 cả ngày, 1 sáng, 2 trưa, 3 tối)

    # Giá cả
    price_level = models.IntegerField(default=1) # [1] (1: dưới 100k/đơn vị/người)  (đơn vị có thể là đêm hoặc bữa)
    min_price = models.FloatField(null=True, blank=True)
    max_price = models.FloatField(null=True, blank=True)

    # Giảm giá và sự ưu tiên
    has_surge_price = models.BooleanField(default=False, help_text="Có tăng giá cuối tuần/lễ không") # Có chương trình giảm giá hay không
    discounts = models.ArrayField(model_container=Discount, blank=True, default=list)
    priority = models.IntegerField(default=0) # Điểm được tính dựa vào discounts

    # Đánh giá
    review_count = models.IntegerField(default=0) # Số lượng đánh giá
    rating = models.FloatField(default=0.0, help_text="Điểm đánh giá trung bình từ 0 đến 5")
    rating_bucket = models.IntegerField(default=0) # Là rating nhưng làm tròn xuống

    # Comment
    comments = models.ArrayField(model_container=Comment, blank=True, default=list)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['-rating_bucket', '-priority', 'price_level']),
        ]
    

    # Tự động lưu rating_bucket
    def save(self, *args, **kwargs):
        # Tự động đồng bộ latitude/longitude vào field location trước khi lưu
        # Lưu ý: Longitude (Kinh độ) phải đứng trước Latitude (Vĩ độ)
        if hasattr(self, 'longitude') and hasattr(self, 'latitude'):
            self.location = {
                "type": "Point",
                "coordinates": [float(self.longitude), float(self.latitude)]
            }
        
        # Logic tự động lưu rating_bucket
        self.rating_bucket = int(self.rating)
        super().save(*args, **kwargs)


# --- 3 Bảng riêng biệt (3 Collection trong MongoDB) ---
class Restaurant(CommonInfo):
    cuisine_types = models.JSONField(default=list, blank=True)
    menus = models.ArrayField(model_container=Menu)

    class Meta(CommonInfo.Meta):
        abstract = False
        pass

class Hotel(CommonInfo):
    hotel_type = models.IntegerField()
    room_list = models.ArrayField(model_container=RoomPrice)

    class Meta(CommonInfo.Meta):
        abstract = False
        indexes = CommonInfo.Meta.indexes + [
            models.Index(fields=['hotel_type', '-rating_bucket', '-priority', 'price_level']),
        ]

class Attraction(CommonInfo):
    tags = models.JSONField(default=list, blank=True)

    class Meta(CommonInfo.Meta):
        abstract = False
        pass