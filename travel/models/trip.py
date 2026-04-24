from djongo import models
from django.conf import settings



def default_dict(): return {}
def default_list(): return []


class TravelInput(models.Model):
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    num_people = models.IntegerField(default=1)
    area = models.IntegerField()

    # Ngày đi và ngày về
    departure_date = models.DateField() 
    return_date = models.DateField()    
    
    # Phần trăm ngân sách cho từng hạn mục
    percentage_hotel = models.IntegerField(default=30, null=False, blank=False)
    percentage_restaurant = models.IntegerField(default=35, null=False, blank=False)
    percentage_attraction = models.IntegerField(default=30, null=False, blank=False)

    # Các trường này cho phép để trống
    location = models.CharField(max_length=24, null=True, blank=True)
    travel_style = models.JSONField(default=default_list, blank=True)
    food_type = models.JSONField(default=default_list, blank=True)
    accommodation_type = models.JSONField(default=default_list, blank=True)

    def __str__(self):
        return f"Trip to {self.area} for {self.num_people} people"


class TravelOutput(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    # Kết nối với User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='travel_outputs'
    )

    # Lưu ID của bản ghi Input đã tạo ra lịch trình này
    # Dùng CharField để linh hoạt (có thể lưu ObjectId của MongoDB)
    input_id = models.CharField(max_length=100, verbose_name="ID Input gốc")

    # Thông tin tổng kết (lưu hai cái dict, 
    # một là summary_info gồm (obj hotel, main_location (cái này chỉ có tên thôi)
    # hai là budget_breakdown gồm chi phí các loại hình)
    summary_info = models.JSONField(default=default_dict, blank=True, verbose_name="Thông tin tổng kết")

    # Lịch trình chi tiết theo từng ngày
    # Mỗi phần tử trong list là 1 dict đại diện cho 1 ngày
    itinerary = models.JSONField(default=default_list, blank=True, verbose_name="Lịch trình chi tiết")
    ''' Cấu trúc từng ngày
    {
        "day": 1,
        "meals": {
            "breakfast": "id_quan_pho_1",
            "lunch": "id_quan_com_2",
            "dinner": "id_nha_hang_3"
        },
        "activities": ["id_vinh_nha_trang", "id_thap_ba_ponagar"], # Ngày 1 đi 2 chỗ
        "note": "Nên đi sớm để tránh nắng"
    }
    '''

    class Meta:
        verbose_name = "Kết quả lịch trình"
        verbose_name_plural = "Danh sách kết quả"
        indexes = [
            models.Index(fields=['input_id']),
        ]

    def __str__(self):
        # Hiển thị thời gian tạo và số ngày để dễ phân biệt
        local_time = self.created_at.strftime("%d/%m/%Y %H:%M")
        return f"Lịch trình ngày {local_time} - ({len(self.itinerary)} ngày)"


class Location(models.Model):
    name = models.CharField(max_length=255, help_text="Tên hiển thị (vd: Vinpearl Land)")
    # search_name dùng để tìm kiếm không dấu, viết thường giúp query cực nhanh
    search_name = models.CharField(max_length=255, help_text="vd: vinpearl land")

    # Tọa độ chuẩn GeoJSON để dùng 2dsphere
    coordinate = models.JSONField(default=default_dict, blank=True) 
    # Cấu trúc lưu: {"type": "Point", "coordinates": [long, lat]}

    is_city = models.BooleanField(default=default_list, blank=True)
    # Bán kính gợi ý khi tìm kiếm quanh điểm này (đơn vị: mét)
    # Thành phố có thể để 20000 (20km), điểm cụ thể để 2000 (2km)
    suggested_radius = models.IntegerField(default=5000)

    class Meta:
        verbose_name = "Địa điểm hệ thống"
        # Đánh index cho search_name để tìm kiếm tên địa danh tức thì
        indexes = [
            # Đặt tên index cụ thể để tránh Django tự sinh tên loằng ngoằng
            models.Index(fields=['search_name'], name='idx_location_search_name'),
        ]

    def __str__(self):
        return f"{self.name}"

