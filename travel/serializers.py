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
        fields = '__all__'

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