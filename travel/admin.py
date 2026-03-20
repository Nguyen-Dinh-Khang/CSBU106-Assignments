from django.contrib import admin
from .models import Hotel, Restaurant, Location, Attraction # Thêm các model khác của bạn vào đây

# Đăng ký các model để chúng hiện lên trang Admin
admin.site.register(Hotel)
admin.site.register(Restaurant)
admin.site.register(Location)
admin.site.register(Attraction)