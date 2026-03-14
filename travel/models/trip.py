from djongo import models
from django.conf import settings

class TravelInput(models.Model):
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    num_people = models.IntegerField(default=1)
    city = models.IntegerField()
    travel_style = models.IntegerField()

    # Ngày đi và ngày về
    departure_date = models.DateField() 
    return_date = models.DateField()    
    
    # Các trường này cho phép để trống
    location = models.IntegerField(null=True, blank=True)
    food_type = models.IntegerField(null=True, blank=True)
    accommodation_type = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Trip to {self.city} for {self.num_people} people"


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

    # Thông tin tổng kết (Tổng chi phí, lưu ý chung, tips...)
    summary_info = models.JSONField(default=dict, verbose_name="Thông tin tổng kết")

    # Lịch trình chi tiết theo từng ngày
    # Mỗi phần tử trong list là 1 dict đại diện cho 1 ngày
    itinerary = models.JSONField(default=list, verbose_name="Lịch trình chi tiết")
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
    search_name = models.CharField(max_length=255, db_index=True, help_text="vd: vinpearl land")

    # Tọa độ chuẩn GeoJSON để dùng 2dsphere
    coordinate = models.JSONField(default=dict) 
    # Cấu trúc lưu: {"type": "Point", "coordinates": [long, lat]}

    # Bán kính gợi ý khi tìm kiếm quanh điểm này (đơn vị: mét)
    # Thành phố có thể để 20000 (20km), điểm cụ thể để 2000 (2km)
    suggested_radius = models.IntegerField(default=5000)

    class Meta:
        verbose_name = "Địa điểm hệ thống"
        # Đánh index cho search_name để tìm kiếm tên địa danh tức thì
        indexes = [
            models.Index(fields=['search_name']),
        ]

    def __str__(self):
        return f"{self.name}"

