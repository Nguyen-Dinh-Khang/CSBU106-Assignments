from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from ..serializers import RestaurantSerializer, HotelSerializer, AttractionSerializer, UserSerializer, LocationSerializer, TravelInputSerializer, TravelOutputSerializer
from ..models import Restaurant, Hotel, Attraction, User, TravelInput, TravelOutput, Location