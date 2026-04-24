from rest_framework import serializers
from .models import User, Restaurant, Hotel, Attraction, Location, TravelInput, TravelOutput, Dish, RoomTypePrice, Discount, Comment


# --- Dish Serializer ------------------------------------------------------------------
class DishSerializer(serializers.Serializer):
    dish_id = serializers.UUIDField(required=False)
    dish_name = serializers.CharField(max_length=100)
    price = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

# --- RoomTypePrice Serializer ---------------------------------------------------------
class RoomTypePriceSerializer(serializers.Serializer):
    room_type_id = serializers.UUIDField(required=False)
    type_name = serializers.CharField(max_length=100)
    price = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

# --- Discount Serializer --------------------------------------------------------------
class DiscountSerializer(serializers.Serializer):
    discount_id = serializers.UUIDField(required=False)
    title = serializers.CharField(max_length=200)
    percent = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

# --- Comment Serializer ---------------------------------------------------------------
class CommentSerializer(serializers.Serializer):
    comment_id = serializers.UUIDField(required=False)
    user_id = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    commenter = serializers.CharField(max_length=100)
    content = serializers.CharField()
    date = serializers.DateTimeField(required=False, allow_null=True)

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
        fields = ['id', 'email', 'username', 'password', 'role', 'type_location']
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {'read_only': True},
            'type_location': {'read_only': True}
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
        type_location = 'NONE'
        
        # 2. Lấy request từ context (DRF tự động truyền request vào context khi gọi từ View)
        request = self.context.get('request')
        
        # 3. Kiểm tra: Nếu có người dùng đang đăng nhập VÀ người đó là ADMIN
        # (Lưu ý: user.role == 'ADMIN' dựa trên Model User bạn đã định nghĩa)
        if request and request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN':
            # Chỉ lúc này mới cho phép lấy role từ dữ liệu gửi lên (nếu có)
            role = validated_data.get('role', 'USER')
            type_location = validated_data.get('type_location', 'NONE')

        # 4. Tạo User với role đã được "thẩm định"   
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            role=role,
            type_location=type_location
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