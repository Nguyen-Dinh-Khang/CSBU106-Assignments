from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
import random

from ..models import Location, Restaurant, Hotel, Attraction
from ..serializers import RestaurantSerializer, HotelSerializer, AttractionSerializer

# === Vận hành ModelViewSet cho mục #10 (Tạo địa điểm) ===

class PlaceBaseViewSet(viewsets.ModelViewSet):
    """
    10: Tạo địa điểm và CRUD
    Dùng chung ModelViewSet cho Restaurant, Hotel, Attraction
    Tự động gán user request vào field user_id (giả lập owner).
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        # Thiết lập user_id là người tạo ra từ request thay vì từ data
        serializer.save(user=self.request.user)

class RestaurantViewSet(PlaceBaseViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

class HotelViewSet(PlaceBaseViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer

class AttractionViewSet(PlaceBaseViewSet):
    queryset = Attraction.objects.all()
    serializer_class = AttractionSerializer


# === Mục 5, 6: Browse và Detail ===

class PlaceBrowseView(APIView):
    """
    5: List địa điểm (trường hợp Lần đầu / Sau đó)
    """
    def get(self, request):
        try:
            filters = request.GET.dict()
            has_filters = any(k in ["travel_style", "food_type", "accommodation_type"] for k in filters.keys())

            # Cần trả về format {"Hotels": [...], "Restaurants": [...], "Attractions": [...]}
            # Các data chỉ gồm id, name, address, rating, price_level
            
            response_data = {}
            if not has_filters:
                # Lần đầu: Random 12 items
                # Do Django ORM random sẽ là ? order_by('?')
                h_qs = Hotel.objects.order_by('?')[:12].values('id', 'name', 'address', 'rating', 'price_level')
                r_qs = Restaurant.objects.order_by('?')[:12].values('id', 'name', 'address', 'rating', 'price_level')
                a_qs = Attraction.objects.order_by('?')[:12].values('id', 'name', 'address', 'rating', 'price_level')
                
                response_data = {
                    "Hotels": list(h_qs),
                    "Restaurants": list(r_qs),
                    "Attractions": list(a_qs)
                }
            else:
                # Có filter: Mỗi lần chỉ 1 loại với 12 object
                if "accommodation_type" in filters:
                    h_qs = Hotel.objects.filter(hotel_type=filters["accommodation_type"])[:12].values('id', 'name', 'address', 'rating', 'price_level')
                    response_data = {"Hotels": list(h_qs)}
                elif "food_type" in filters:
                    r_qs = Restaurant.objects.filter(cuisine_types__contains=filters["food_type"])[:12].values('id', 'name', 'address', 'rating', 'price_level')
                    response_data = {"Restaurants": list(r_qs)}
                elif "travel_style" in filters:
                    a_qs = Attraction.objects.filter(tags__contains=filters["travel_style"])[:12].values('id', 'name', 'address', 'rating', 'price_level')
                    response_data = {"Attractions": list(a_qs)}
                    
            return Response(response_data, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlaceDetailUniversalView(APIView):
    """
    6: Thông tin chi tiết
    Lấy ID truy xuất vào 3 bảng
    """
    def get(self, request, place_id):
        try:
            # Detect collection
            if Restaurant.objects.filter(id=place_id).exists():
                serializer = RestaurantSerializer(Restaurant.objects.get(id=place_id))
            elif Hotel.objects.filter(id=place_id).exists():
                serializer = HotelSerializer(Hotel.objects.get(id=place_id))
            elif Attraction.objects.filter(id=place_id).exists():
                serializer = AttractionSerializer(Attraction.objects.get(id=place_id))
            else:
                return Response({"success": False, "message": "Không tìm thấy địa điểm"}, status=status.HTTP_404_NOT_FOUND)
                
            return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
