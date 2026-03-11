from djongo import models
import uuid

# --- Cấu trúc Nhúng (Embedded Models) ---

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

# --- Model Chính (Main Document) ---

# --- Abstract Model để đỡ phải gõ lại các trường chung ---
class CommonInfo(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # Chủ sở hữu
    owner = models.OneToOneField(
        'travel.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'OWNER'}, # Chỉ hiện danh sách các Owner trong Admin
        related_name="owned_%(class)s"      # Tạo tên ngược: user.owned_restaurant, user.owned_hotel...
    )

    # Tọa độ
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Thời gian hoạt động
    off_days = models.JSONField(default=list)
    active_slots = models.JSONField(default=list)

    # Giảm giá và sự ưu tiên
    has_surge_price = models.BooleanField(default=False, help_text="Có tăng giá cuối tuần/lễ không")
    discounts = models.ArrayField(model_container=Discount, blank=True, null=True)
    priority = models.IntegerField(default=0)

    # Đánh giá
    review_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0, help_text="Điểm đánh giá trung bình từ 0 đến 5")
    rating_bucket = models.IntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['-rating_bucket', '-priority']),
        ]
    
    # Tự động lưu rating_bucket
    def save(self, *args, **kwargs):
        self.rating_bucket = int(self.rating)
        super().save(*args, **kwargs)


# --- 3 Bảng riêng biệt (3 Collection trong MongoDB) ---
class Restaurant(CommonInfo):
    cuisine_types = models.JSONField(default=list, blank=True)
    menus = models.ArrayField(model_container=Menu)

    class Meta:
        indexes = [
            models.Index(fields=['cuisine_types']), 
        ]

class Hotel(CommonInfo):
    star_class = models.IntegerField()
    room_rates = models.ArrayField(model_container=RoomPrice)

class Attraction(CommonInfo):
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['tags']),
        ]