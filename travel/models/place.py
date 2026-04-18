from djongo import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

# --- Cấu trúc Nhúng (Embedded Models) ---

# --- Menu quán ăn ----------------------------------------------------------------------------------------------------------------
class Dish(models.Model):
    dish_id = models.UUIDField(default=uuid.uuid4, editable=False)
    dish_name = models.CharField(max_length=100)
    price = models.IntegerField()
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    class Meta:
        abstract = True # Dùng để nhúng, không tạo bảng riêng

# --- Giá phòng khác sạn ----------------------------------------------------------------------------------------------------------
class RoomTypePrice(models.Model):
    room_type_id = models.UUIDField(default=uuid.uuid4, editable=False)
    type_name = models.CharField(max_length=100) # VD: Deluxe, Standard
    price = models.IntegerField()
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    class Meta:
        abstract = True

# --- Giảm giá --------------------------------------------------------------------------------------------------------------------
class Discount(models.Model):
    discount_id = models.UUIDField(default=uuid.uuid4, editable=False)
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
    comment_id = models.UUIDField(default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=50)
    commenter = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

# ---------------------------------------------------------------------------------------------------------------------------------
# --- Model Chính (Main Document) -------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------------------
def get_default_location():
    return {"type": "Point", "coordinates": [0.0, 0.0]} # Một giá trị mặc định hợp lệ

def get_default_list():
    return []
# --- Abstract Model để đỡ phải gõ lại các trường chung ---
class CommonInfo(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, help_text="Thông tin chi tiết")

    # Chủ sở hữu
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'OWNER'},
        related_name="owned_%(class)s",
        null=True,   # Giữ lại để cho phép chưa có chủ
        blank=True
    )

    # Tọa độ
    latitude = models.FloatField()  # Trong khoảng [-90, 90] 
    longitude = models.FloatField() # Trong khoảng [-180, 180]
    location = models.JSONField(default=get_default_location, blank=True) # Tự động lưu
    # location = models.JSONField(default=dict)

    # Thời gian hoạt động
    off_weekdays = models.JSONField(default=get_default_list) # [1, 7] (1: chủ nhật, 7: thứ 7)
    off_dates = models.JSONField(default=get_default_list)    # ["01-01", "30-04", "01-05"] (ngày-tháng)
    active_hours = models.JSONField(default=get_default_list) # [1, 3] (0 cả ngày, 1 sáng, 2 trưa, 3 tối)

    # Giá cả
    price_level = models.IntegerField(default=1) # [1] (1: dưới 100k/đơn vị/người)  (đơn vị có thể là đêm hoặc bữa)
    min_price = models.FloatField(null=True, blank=True)
    max_price = models.FloatField(null=True, blank=True)

    # Giảm giá và sự ưu tiên
    has_surge_price = models.BooleanField(default=False, help_text="Có tăng giá cuối tuần/lễ không") # Có chương trình giảm giá hay không
    discounts = models.ArrayField(model_container=Discount, blank=True, default=[])
    priority = models.IntegerField(default=0) # Điểm được tính dựa vào discounts

    # Đánh giá
    review_count = models.IntegerField(default=0) # Số lượng đánh giá
    rating = models.FloatField(default=0.0, help_text="Điểm đánh giá trung bình từ 0 đến 5")
    rating_bucket = models.IntegerField(default=0) # Là rating nhưng làm tròn xuống

    # Comment
    comments = models.ArrayField(model_container=Comment, blank=True, default=[])

    class Meta:
        abstract = True
        # indexes = [
        #     models.Index(fields=['-rating_bucket', '-priority', 'price_level']),
        # ]
    

    def update_priority(self):
        """
        Logic: Tự động lọc bỏ các discount hết hạn và tính toán lại điểm priority.
        Hàm này thay đổi trực tiếp dữ liệu trên instance (gán luôn).
        """
        today = timezone.now().date()
        
        # 1. Kiểm tra nếu không có discount nào thì reset và thoát sớm
        if not self.discounts:
            self.priority = 0
            self.has_surge_price = False
            return

        # 2. LỌC: Gán lại danh sách discounts (Chỉ giữ cái còn hạn hoặc vô thời hạn)
        self.discounts = [
            d for d in self.discounts 
            if getattr(d, 'end_date', None) is None or d.end_date >= today
        ]

        # 3. TÍNH TOÁN: Dựa trên danh sách đã lọc ở bước 2
        if self.discounts:
            total_percent = sum(getattr(d, 'percent', 0) for d in self.discounts)
            self.priority = int(total_percent / len(self.discounts))
            self.has_surge_price = True
        else:
            self.priority = 0
            self.has_surge_price = False

    # --- HÀM SAVE CHÍNH ---
    def save(self, *args, **kwargs):
        # 1. Kiểm tra điều kiện Latitude và Longitude
        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValidationError(f"Vĩ độ (latitude) {self.latitude} phải nằm trong khoảng [-90, 90].")
        
        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValidationError(f"Kinh độ (longitude) {self.longitude} phải nằm trong khoảng [-180, 180].")
            
        # 2. Tự động xử lý Discount và Priority
        self.update_priority()

        # 3. Tự động đồng bộ latitude/longitude vào field location
        if hasattr(self, 'longitude') and hasattr(self, 'latitude'):
            # Đảm bảo longitude/latitude không bị None trước khi ép kiểu float
            if self.longitude is not None and self.latitude is not None:
                self.location = {
                    "type": "Point",
                    "coordinates": [float(self.longitude), float(self.latitude)]
                }
        
        # 4. Tự động cập nhật rating_bucket (làm tròn xuống từ rating)
        # Sử dụng getattr để an toàn nếu rating chưa được khởi tạo
        current_rating = getattr(self, 'rating', 0)
        self.rating_bucket = int(current_rating)

        # 5. ÉP KIỂU CHO CÁC TRƯỜNG ARRAY/JSON (Quan trọng để fix lỗi [])
        # Nếu các trường này bị None hoặc là chuỗi rỗng từ Admin gửi về, ta ép nó về []
        if not isinstance(self.off_weekdays, list): self.off_weekdays = []
        if not isinstance(self.off_dates, list): self.off_dates = []
        if not isinstance(self.active_hours, list): self.active_hours = []
        if not isinstance(self.discounts, list): self.discounts = []
        if not isinstance(self.comments, list): self.comments = []
        
        # Riêng với Attraction/Hotel/Restaurant (các trường riêng)
        if hasattr(self, 'tags') and not isinstance(self.tags, list): self.tags = []
        if hasattr(self, 'cuisine_types') and not isinstance(self.cuisine_types, list): self.cuisine_types = []

        # 6. Gọi hàm save của cha để ghi dữ liệu xuống Database
        super().save(*args, **kwargs)

# --- 3 Bảng riêng biệt (3 Collection trong MongoDB) ---
class Restaurant(CommonInfo):
    cuisine_types = models.JSONField(default=get_default_list, blank=True)
    dishes = models.ArrayField(model_container=Dish, blank=True, default=[])
    image = models.ImageField(upload_to='restaurant/', null=True, blank=True)

    class Meta:
        # (CommonInfo.Meta)
        abstract = False
        indexes = [
            models.Index(fields=['-rating_bucket', '-priority', 'price_level']),
        ]
        # pass

class Hotel(CommonInfo):
    hotel_type = models.IntegerField()
    room_types = models.ArrayField(model_container=RoomTypePrice, blank=True, default=[])
    image = models.ImageField(upload_to='hotel/', null=True, blank=True)


    class Meta:
        # (CommonInfo.Meta)
        abstract = False
        indexes = [
            models.Index(fields=['-rating_bucket', '-priority', 'price_level']),
            models.Index(fields=['hotel_type', '-rating_bucket', '-priority', 'price_level']),
        ]

class Attraction(CommonInfo):
    tags = models.JSONField(default=get_default_list, blank=True)
    image = models.ImageField(upload_to='attraction/', null=True, blank=True)


    class Meta:
        # (CommonInfo.Meta)
        abstract = False
        indexes = [
            models.Index(fields=['-rating_bucket', '-priority', 'price_level']),
        ]
        # pass