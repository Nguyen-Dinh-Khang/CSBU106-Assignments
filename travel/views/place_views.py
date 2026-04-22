from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
import random
import uuid

from ..models import Location, Restaurant, Hotel, Attraction, Discount, Dish, RoomTypePrice, Comment
from ..serializers import RestaurantSerializer, HotelSerializer, AttractionSerializer






# My location:
class MyPlaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Kiểm tra loại địa điểm của user
        if user.type_location == 'RESTAURANT':
            # Giả sử bạn đã đặt related_name="owned_restaurant" ở model Restaurant
            place = getattr(user, 'owned_restaurant', None)
            serializer_class = RestaurantSerializer 
        elif user.type_location == 'ACCOMMODATION':
            place = getattr(user, 'owned_hotel', None)
            serializer_class = HotelSerializer
        elif user.type_location == 'ENTERTAINMENT':
            place = getattr(user, 'owned_attraction', None)
            serializer_class = AttractionSerializer
        else:
            return Response({"detail": "Bạn chưa cấu hình loại địa điểm."}, status=400)

        if not place:
            return Response({"detail": "Bạn chưa tạo địa điểm nào."}, status=404)

        serializer = serializer_class(place)
        return Response(serializer.data)


# Vận hành ModelViewSet cho mục #10 (Tạo địa điểm)

class PlaceBaseViewSet(viewsets.ModelViewSet):
    """
    10: Tạo địa điểm và CRUD
    Dùng chung ModelViewSet cho Restaurant, Hotel, Attraction
    Tự động gán user request vào field user_id (giả lập owner).
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        # 10: Tạo địa điểm, owner được tự động lấy từ request, user không thể gửi tự chỉnh
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        # 10.1: Chỉnh sửa địa điểm (Chỉ owner mới được sửa)
        if self.get_object().owner != self.request.user:
            raise PermissionDenied("Chỉ chủ sở hữu (owner) mới có quyền chỉnh sửa địa điểm.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise PermissionDenied("Chỉ chủ sở hữu (owner) mới có quyền xóa địa điểm.")
        instance.delete()

    # 10.5: Thêm/Sửa/Xóa discount
    @action(detail=True, methods=['post', 'put', 'delete'], url_path='discounts')
    def manage_discounts(self, request, pk=None):
        instance = self.get_object()
        if instance.owner != request.user:
            return Response({"success": False, "message": "Bạn không phải owner, không thể thao tác discount."}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'POST':
            # Create discount
            data = request.data
            try:
                discount = Discount(
                    discount_id=uuid.uuid4(),
                    title=data.get('title'),
                    percent=int(data.get('percent', 0)),
                    description=data.get('description', ''),
                    start_date=data.get('start_date'),
                    end_date=data.get('end_date')
                )
                instance.discounts.append(discount)
                instance.save()
                return Response({"success": True, "message": "Thêm giảm giá (Discount) thành công", "id": str(discount.discount_id)}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        elif request.method == 'PUT':
            # Edit discount
            d_id = request.data.get('discount_id')
            for d in instance.discounts:
                if str(d.discount_id) == str(d_id):
                    d.title = request.data.get('title', d.title)
                    if 'percent' in request.data: d.percent = int(request.data.get('percent'))
                    d.description = request.data.get('description', d.description)
                    d.start_date = request.data.get('start_date', d.start_date)
                    d.end_date = request.data.get('end_date', d.end_date)
                    instance.save()
                    return Response({"success": True, "message": "Sửa giảm giá thành công"}, status=status.HTTP_200_OK)
            return Response({"success": False, "message": "Không tìm thấy discount_id phù hợp"}, status=status.HTTP_404_NOT_FOUND)
            
        elif request.method == 'DELETE':
            d_id = request.data.get('discount_id')
            instance.discounts = [d for d in instance.discounts if str(d.discount_id) != str(d_id)]
            instance.save()
            return Response({"success": True, "message": "Xóa giảm giá thành công"}, status=status.HTTP_200_OK)

    # 10.9: Thêm comment
    @action(detail=True, methods=['post'], url_path='comments')
    def add_comment(self, request, pk=None):
        instance = self.get_object()
        if not request.user.is_authenticated:
            return Response({"success": False, "message": "Bạn cần đăng nhập để bình luận."}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            comment = Comment(
                comment_id=uuid.uuid4(),
                user_id=str(request.user.id),
                commenter=request.user.username or "Khách",
                content=request.data.get('content', ''),
                date=timezone.now()
            )
            instance.comments.append(comment)
            instance.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 11: Đánh giá sao
    @action(detail=True, methods=['post'], url_path='rate')
    def rate_star(self, request, pk=None):
        instance = self.get_object()
        try:
            star = float(request.data.get('star', 0))
            if not (0 <= star <= 5):
                return Response({"success": False, "message": "Số sao đánh giá phải từ 0 đến 5"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Cập nhật số liệu rating trung bình và lượt đánh giá
            new_rating = ((instance.rating * instance.review_count) + star) / (instance.review_count + 1)
            instance.rating = round(new_rating, 2)
            instance.review_count += 1
            instance.save()
            
            return Response({"success": True, "message": f"Cập nhật rating thành công: {instance.rating}"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": f"Sai định dạng dữ liệu: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class RestaurantViewSet(PlaceBaseViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

    # 10.7 Thêm sửa xóa Menu/Món ăn
    @action(detail=True, methods=['post', 'put', 'delete'], url_path='menu')
    def manage_menu(self, request, pk=None):
        instance = self.get_object()
        if instance.owner != request.user:
            return Response({"success": False, "message": "Bạn không phải chủ sở hữu, không quản lý được menu."}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'POST':
            dish = Dish(
                dish_id=uuid.uuid4(),
                dish_name=request.data.get('dish_name'),
                price=int(request.data.get('price', 0)),
                description=request.data.get('description', '')
            )
            instance.dishes.append(dish)
            instance.save()
            return Response({"success": True, "message": "Thêm món thành công", "id": str(dish.dish_id)}, status=status.HTTP_200_OK)
            
        elif request.method == 'PUT':
            d_id = request.data.get('dish_id')
            for d in instance.dishes:
                if str(d.dish_id) == str(d_id):
                    d.dish_name = request.data.get('dish_name', d.dish_name)
                    if 'price' in request.data: d.price = int(request.data.get('price'))
                    d.description = request.data.get('description', d.description)
                    instance.save()
                    return Response({"success": True, "message": "Sửa món thành công"}, status=status.HTTP_200_OK)
            return Response({"success": False, "message": "Không tìm thấy món ăn"}, status=status.HTTP_404_NOT_FOUND)
            
        elif request.method == 'DELETE':
            d_id = request.data.get('dish_id')
            instance.dishes = [d for d in instance.dishes if str(d.dish_id) != str(d_id)]
            instance.save()
            return Response({"success": True, "message": "Xóa món thành công"}, status=status.HTTP_200_OK)

class HotelViewSet(PlaceBaseViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer

    # 10.8 Thêm sửa xóa danh sách phòng khách sạn
    @action(detail=True, methods=['post', 'put', 'delete'], url_path='rooms')
    def manage_rooms(self, request, pk=None):
        instance = self.get_object()
        if instance.owner != request.user:
            return Response({"success": False, "message": "Bạn không phải chủ sở hữu, không thay đổi phòng được."}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'POST':
            room = RoomTypePrice(
                room_type_id=uuid.uuid4(),
                type_name=request.data.get('type_name'),
                price=int(request.data.get('price', 0)),
                description=request.data.get('description', '')
            )
            instance.room_types.append(room)
            instance.save()
            return Response({"success": True, "message": "Thêm phòng thành công", "id": str(room.room_type_id)}, status=status.HTTP_200_OK)
            
        elif request.method == 'PUT':
            r_id = request.data.get('room_type_id')
            for r in instance.room_types:
                if str(r.room_type_id) == str(r_id):
                    r.type_name = request.data.get('type_name', r.type_name)
                    if 'price' in request.data: r.price = int(request.data.get('price'))
                    r.description = request.data.get('description', r.description)
                    instance.save()
                    return Response({"success": True, "message": "Sửa phòng thành công"}, status=status.HTTP_200_OK)
            return Response({"success": False, "message": "Không tìm thấy phòng khách sạn"}, status=status.HTTP_404_NOT_FOUND)
            
        elif request.method == 'DELETE':
            r_id = request.data.get('room_type_id')
            instance.room_types = [r for r in instance.room_types if str(r.room_type_id) != str(r_id)]
            instance.save()
            return Response({"success": True, "message": "Xóa phòng thành công"}, status=status.HTTP_200_OK)

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
                # Có filter: Mỗi lần chỉ lọc 1 loại
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
    Lấy ID truy xuất tự động và parse đúng dữ liệu
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
        