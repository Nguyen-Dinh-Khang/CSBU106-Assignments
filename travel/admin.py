from django.contrib import admin
from .models import *

# Đăng ký các model để chúng hiện lên trang Admin
admin.site.register(User)
admin.site.register(Location)


# Những model phức tạp thì dùng Class để cấu hình exclude
# Xữa lỗi dữ liệu không thể save trong admin
@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    # Loại bỏ các trường gây lỗi JSON/Array và các trường tự động tính toán
    exclude = (
        'location', 'discounts', 'comments', 
        'rating_bucket', 'priority', 'off_weekdays', 
        'off_dates', 'active_hours', 'has_surge_price'
    )
    list_display = ('name', 'address', 'rating', 'priority')

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    exclude = (
        'location', 'discounts', 'comments', 
        'rating_bucket', 'priority', 'off_weekdays', 
        'off_dates', 'active_hours', 'room_types', 'has_surge_price'
    )
    list_display = ('name', 'hotel_type', 'rating')

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    exclude = (
        'location', 'discounts', 'comments', 
        'rating_bucket', 'priority', 'off_weekdays', 
        'off_dates', 'active_hours', 'dishes', 'has_surge_price'
    )
    list_display = ('name', 'price_level', 'rating')