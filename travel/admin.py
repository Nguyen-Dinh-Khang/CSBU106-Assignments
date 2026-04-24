from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Location, Attraction, Hotel, Restaurant



# --- Cấu hình cho Model User ---
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Hiển thị danh sách ở trang chủ Admin
    list_display = ('id', 'email', 'username', 'role')
    
    # Cho phép tìm kiếm nhanh
    search_fields = ('email', 'username', 'role')
    
    # Phân nhóm thông tin khi bấm vào xem chi tiết User
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'type_location')}),
    )
    
    # Cho phép thêm các trường này khi tạo User mới trong Admin
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'type_location')}),
    )


class ReadOnlyAdmin(admin.ModelAdmin):
    """
    Lớp base giúp biến các model thành chế độ: Xem & Xóa.
    Triệt tiêu hoàn toàn khả năng chỉnh sửa để tránh lỗi dữ liệu phức tạp.
    """
    def has_add_permission(self, request):
        return False  # Không cho thêm mới tại Admin

    def has_change_permission(self, request, obj=None):
        return False  # Không cho sửa (Nút Save sẽ biến mất)

    def has_delete_permission(self, request, obj=None):
        return True   # Vẫn giữ lại quyền Xóa

    # Tự động biến mọi trường thành readonly để hiển thị dữ liệu
    def get_readonly_fields(self, request, obj=None):
        # Tự động lấy tất cả các trường trong Database để hiển thị
        return [field.name for field in self.model._meta.fields]

# --- Đăng ký các Model ---

@admin.register(Location)
class LocationAdmin(ReadOnlyAdmin):
    # Hiển thị ID và các trường của mốc địa chỉ
    list_display = ('id', 'name', 'is_city') # Thay bằng field thực tế bạn có
    # Tự động hiển thị toàn bộ fields nhờ ReadOnlyAdmin

@admin.register(Attraction)
class AttractionAdmin(ReadOnlyAdmin):
    list_display = ('id', 'name', 'tags', 'rating')
    search_fields = ('name', 'owner__username')

@admin.register(Hotel)
class HotelAdmin(ReadOnlyAdmin):
    list_display = ('id', 'name', 'hotel_type', 'rating')
    search_fields = ('name', 'owner__username')

@admin.register(Restaurant)
class RestaurantAdmin(ReadOnlyAdmin):
    list_display = ('id', 'name', 'price_level', 'rating')
    search_fields = ('name', 'owner__username')