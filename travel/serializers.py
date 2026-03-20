from rest_framework import serializers
from .models import User, Restaurant, Hotel, Attraction, Location, TravelInput, TravelOutput

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'

class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = '__all__'

class AttractionSerializer(serializers.ModelSerializer):
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