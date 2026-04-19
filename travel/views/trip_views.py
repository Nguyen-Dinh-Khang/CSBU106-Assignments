from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
import json
import unicodedata
import re

from ..models import Location, TravelOutput, TravelInput

# Có note hàm: CreateTravelPlanView(5 note)



# UTILITIES
def remove_vietnamese_accents(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = text.replace('đ', 'd').replace('Đ', 'd')
    text = text.lower()
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def calculate_budget_breakdown(total_budget, num_people, num_days):
    per_person = total_budget / num_people
    food_budget = per_person * 0.40
    hotel_budget = per_person * 0.35
    other_budget = per_person * 0.25
    food_per_meal = food_budget / (num_days * 3) if num_days > 0 else 0
    num_nights = max(num_days - 1, 1)
    hotel_per_night = hotel_budget / num_nights if num_nights > 0 else 0
    other_per_day = other_budget / num_days if num_days > 0 else 0

    return {
        'per_person': round(per_person, 2),
        'food_budget': round(food_budget, 2),
        'hotel_budget': round(hotel_budget, 2),
        'other_budget': round(other_budget, 2),
        'food_per_meal': round(food_per_meal, 2),
        'hotel_per_night': round(hotel_per_night, 2),
        'other_per_day': round(other_per_day, 2)
    }

def calculate_price_level(amount):
    if amount < 100000:
        return 1
    elif amount < 300000:
        return 2
    elif amount < 500000:
        return 3
    elif amount < 1000000:
        return 4
    else:
        return 5

def find_similar_locations(search_term, threshold=0.6, limit=5):
    # Bổ sung logic tìm kiếm tên giống tương tự
    return []

# DRF VIEWS

class GetAreasView(APIView):
    """
    4.5: Gửi location kèm id
    Khi user bấm vào nút lập kế hoạch thì sẽ lấy ds areas.
    """
    def get(self, request):
        try:
            areas = Location.objects.filter(is_city=True)
            area_dict = {area.name: str(area.id) for area in areas}
            return Response({"area": area_dict}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateTravelPlanView(APIView):
    """
    4: Lập kế hoạch
    """

# Có một số cái không cần input nhưng mình vẫn cần lọc á. Sau khi đã làm xong cái đống bên dưới (lấy dữ liệu từ database)
# rồi thì mình còn phải lấy cái đống dữ liệu đó để check xem địa điểm đó có nở cửa giờ đó hay ngày đó không. Còn phải kiểm 
# tra xem địa điểm đó có bị trùng trong các ngày khác không á. Đề xuất của tui là chỉ lọc quán ăn một lần rồi bắt đầu
# chia đều cái danh sách đó ra cho các buổi. Nhớ là không được lọc hai lần cùng một loại hình, lọc lần nào chắc lần đấy. Thêm 
# một điều nữa là khi lọc và thêm vào danh sách thì nhớ chỉnh sữa dữ liệu rồi mới gửi cho frontend. Dữ liệu được gửi đi chỉ có 
# các thuộc tính id, name, has_surge_price, img (sẽ có ảnh thật hoặc là null), tag (hoặc tương tự của mấy loại hình khác). Chỉ gửi cho frontend những cái thật sự cần thiết. Cái 
# nào cần để tự mình lọc thì cứ lấy, nhưng sau khi lọc phải bỏ nó ra.

# Trước khi xử lí output thì nhớ lưu lại input vào model TravelInput, sau khi lưu thì gửi id của input này đi kèm luôn

# Ông chưa có gửi đi thông tin summary, nó bao gồm một object hotel và main_location (lưu cái tên ở đây và ưu tiên chọn 
# location hơn là area)

    def post(self, request):
        try:
            data = request.data
            required_fields = ['budget', 'num_people', 'area', 'departure_date', 'return_date']
            for field in required_fields:
                if field not in data:
                    return Response({'success': False, 'message': f'Thiếu trường bắt buộc: {field}'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                departure_date = datetime.strptime(data['departure_date'], '%Y-%m-%d').date()
                return_date = datetime.strptime(data['return_date'], '%Y-%m-%d').date()
            except ValueError:
                return Response({'success': False, 'message': 'Ngày sai định dạng (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
            
            if departure_date >= return_date:
                return Response({'success': False, 'message': 'Ngày về phải sau ngày đi'}, status=status.HTTP_400_BAD_REQUEST)

            budget = float(data['budget'])
            num_people = int(data['num_people'])
            area_id = data['area']
            

# Chưa có ba cái biến này nha "percentage_hotel (int), percentage_restaurant (int), percentage_attraction (int)"
            location_str = data.get('location',[])
            travel_style = data.get('travel_style', [])
            food_type = data.get('food_type', [])
            accommodation_type = data.get('accommodation_type', [])
            
            num_days = (return_date - departure_date).days + 1
            budget_info = calculate_budget_breakdown(budget, num_people, num_days)
            
            center_coords = None
            if location_str:
                clean_location = remove_vietnamese_accents(location_str)
                location_obj = Location.objects.filter(search_name__icontains=clean_location).first()
                if location_obj:
                    center_coords = location_obj.coordinate.get('coordinates')
                else:
                    return Response({"success": False, "suggested_locations": find_similar_locations(clean_location)}, status=status.HTTP_200_OK)
            else:
                area_obj = Location.objects.filter(id=area_id).first()
                if area_obj:
                    center_coords = area_obj.coordinate.get('coordinates')
                    
            # ... Tiến hành lọc theo requirement (mongodb) -> id, name, has_surge_price, priority -> sort
# Chỗ này là từng object chứ không phải chỉ có cái tên (VD: "Breakfast": obj1). Cấu trúc của mỗi obj thì xem lại file hướng dẫn

            dummy_schedule = [
                {
                    "Date": str(departure_date), 
                    "Breakfast": "...", 
                    "Lunch": "...", 
                    "Dinner": "...", 
                    "Place": ["id_1", "id_2"]
                }
            ]
            
            budget_dict = {
                "food": budget_info["food_budget"],
                "hotel": budget_info["hotel_budget"],
                "other": budget_info["other_budget"]
            }
            
            return Response({
                "budget_breakdown": budget_dict,
                "schedule": dummy_schedule,
                "hotels": [], 
                "restaurants_breakfast": [],
                "restaurants_lunch": [],
                "restaurants_dinner": [],
                "attractions": [],
                "can_change": True
            })
            
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetTravelHistoryView(APIView):
    """
    7: Lấy lịch sử theo ngày tạo mới đến cũ của user id
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        history = TravelOutput.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            "id": str(item.id),
            "created_at": item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "location": item.summary_info.get('location', '')
        } for item in history]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class ViewPlanDetailView(APIView):
    """
    8: Xem chi tiết kế hoạch (can_change=False)
    """
    def get(self, request, plan_id):
        try:
            plan = TravelOutput.objects.get(id=plan_id)
            return Response({
                "budget_breakdown": plan.summary_info,
                "schedule": plan.itinerary,
                "hotel_id": plan.summary_info.get("hotel_id", ""),
                "can_change": False
            }, status=status.HTTP_200_OK)
        except TravelOutput.DoesNotExist:
            return Response({"success": False, "message": "Không tìm thấy"}, status=status.HTTP_404_NOT_FOUND)


class EditPlanView(APIView):
    """
    9: Chỉnh sửa kế hoạch (can_change=True, tái xử lý từ TravelInput)
    """
    def get(self, request, plan_id):
        try:
            plan = TravelOutput.objects.get(id=plan_id)
            input_plan = TravelInput.objects.get(id=plan.input_id)
            
            return Response({
                "budget_breakdown": plan.summary_info,
                "schedule": plan.itinerary,
                "hotel_id": plan.summary_info.get("hotel_id", ""),
                "hotels": [], 
                "restaurants_breakfast": [],
                "restaurants_lunch": [],
                "restaurants_dinner": [],
                "attractions": [],
                "can_change": True
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_404_NOT_FOUND)
