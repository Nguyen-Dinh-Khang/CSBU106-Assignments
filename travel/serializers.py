from rest_framework import serializers
from .models import User, Restaurant, Hotel, Attraction, Location, TravelInput, TravelOutput, Dish, RoomTypePrice, Discount, Comment


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = '__all__'

class RoomTypePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomTypePrice
        fields = '__all__'

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'

class RestaurantSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True, read_only=True)
    discounts = DiscountSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = '__all__'

class HotelSerializer(serializers.ModelSerializer):
    room_types = RoomTypePriceSerializer(many=True, read_only=True)
    discounts = DiscountSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = '__all__'

class AttractionSerializer(serializers.ModelSerializer):
    discounts = DiscountSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Attraction
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {'read_only': True}
        }

    def validate_email(self, value):
        value = value.strip().lower()
        # Lấy danh sách user trùng tên nhưng KHÔNG PHẢI là chính mình (trường hợp update)
        qs = User.objects.filter(email=value)
        
        if self.instance: # Nếu đang là Update
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise serializers.ValidationError("Email đã tồn tại")
        return value

    def validate_username(self, value):
        value = value.strip()
        # Lấy danh sách user trùng tên nhưng KHÔNG PHẢI là chính mình (trường hợp update)
        qs = User.objects.filter(username=value)
        
        if self.instance: # Nếu đang là Update
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise serializers.ValidationError("Username đã tồn tại")
        return value
        
    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("Password quá ngắn")
        return value

    def create(self, validated_data):
        # 1. Mặc định luôn là USER để an toàn
        role = 'USER'
        
        # 2. Lấy request từ context (DRF tự động truyền request vào context khi gọi từ View)
        request = self.context.get('request')
        
        # 3. Kiểm tra: Nếu có người dùng đang đăng nhập VÀ người đó là ADMIN
        # (Lưu ý: user.role == 'ADMIN' dựa trên Model User bạn đã định nghĩa)
        if request and request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN':
            # Chỉ lúc này mới cho phép lấy role từ dữ liệu gửi lên (nếu có)
            role = validated_data.get('role', 'USER')

        # 4. Tạo User với role đã được "thẩm định"   
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            role=role
        )
        user.set_password(validated_data['password'])  # 🔥 cực kỳ quan trọng
        user.save()
        return user
    
class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class TravelInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelInput
        fields = '__all__'

class TravelOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelOutput
        fields = '__all__'