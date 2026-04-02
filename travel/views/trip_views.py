from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
import unicodedata
import re
from difflib import SequenceMatcher
from pymongo import MongoClient
from django.conf import settings

from ..models import Restaurant, Hotel, Attraction, User, TravelInput, TravelOutput, Location


def remove_vietnamese_accents(text):
    """
    Bỏ dấu tiếng Việt và viết thường toàn bộ

    Args:
        text (str): Chuỗi cần xử lý

    Returns:
        str: Chuỗi không dấu, viết thường, đã loại bỏ khoảng trắng dư
    """
    if not text:
        return ""

    # Chuẩn hóa Unicode về dạng NFD (tách ký tự và dấu)
    text = unicodedata.normalize('NFD', text)

    # Loại bỏ các ký tự dấu (combining characters)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

    # Chuyển đ -> d, Đ -> D
    text = text.replace('đ', 'd').replace('Đ', 'd')

    # Viết thường
    text = text.lower()

    # Loại bỏ khoảng trắng thừa (đầu, cuối và giữa)
    text = re.sub(r'\s+', ' ', text.strip())

    return text


def calculate_budget_breakdown(total_budget, num_people, num_days):
    """
    Chia ngân sách thành 3 phần: ăn, ở, hoạt động khác

    Args:
        total_budget (float): Tổng ngân sách
        num_people (int): Số người
        num_days (int): Số ngày

    Returns:
        dict: Ngân sách chi tiết
    """
    per_person = total_budget / num_people

    # Phân chia ngân sách
    food_budget = per_person * 0.40
    hotel_budget = per_person * 0.35
    other_budget = per_person * 0.25

    # Tính chi phí trên mỗi đơn vị
    food_per_meal = food_budget / (num_days * 3) if num_days > 0 else 0

    # Hotel: số đêm = số ngày - 1
    num_nights = max(num_days - 1, 1)
    hotel_per_night = hotel_budget / num_nights if num_nights > 0 else 0

    # Hoạt động khác: chia đều theo số ngày
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
    """
    Tính price_level dựa trên số tiền

    Price level:
    - 1: dưới 100k
    - 2: 100k - 300k
    - 3: 300k - 500k
    - 4: 500k - 1tr
    - 5: trên 1tr

    Args:
        amount (float): Số tiền (VNĐ)

    Returns:
        int: Price level
    """
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
    """
    Tìm các địa điểm có tên tương tự với search_term

    Args:
        search_term (str): Từ khóa tìm kiếm (đã được normalize)
        threshold (float): Ngưỡng độ tương đồng (0-1)
        limit (int): Số lượng kết quả tối đa

    Returns:
        list: Danh sách các địa điểm tương tự
    """
    results = []

    # Lấy tất cả locations
    all_locations = Location.objects.all()

    for location in all_locations:
        # Tính độ tương đồng
        similarity = SequenceMatcher(None, search_term, location.search_name).ratio()

        if similarity >= threshold:
            results.append({
                'id': str(location.id),
                'name': location.name,
                'search_name': location.search_name,
                'similarity': round(similarity, 2)
            })

    # Sắp xếp theo độ tương đồng giảm dần
    results.sort(key=lambda x: x['similarity'], reverse=True)

    return results[:limit]


def get_mongodb_connection():
    """
    Tạo và trả về MongoDB client và database

    Returns:
        tuple: (client, database)
    """
    db_settings = settings.DATABASES['default']
    host = db_settings.get('CLIENT', {}).get('host', 'mongodb://localhost:27017/')

    client = MongoClient(host)
    db = client[db_settings['NAME']]

    return client, db


def query_places_geospatial(collection_name, center_coords, search_radius,
                           price_level, additional_filters=None):
    """
    Query MongoDB với geospatial search

    Args:
        collection_name (str): Tên collection
        center_coords (list): [longitude, latitude]
        search_radius (int): Bán kính tìm kiếm (meters)
        price_level (int): Mức giá tối đa
        additional_filters (dict): Các filter bổ sung

    Returns:
        list: Danh sách kết quả
    """
    client, db = get_mongodb_connection()

    try:
        collection = db[collection_name]

        # Build query filter
        query_filter = {
            'location': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': center_coords
                    },
                    '$maxDistance': search_radius
                }
            },
            'price_level': {'$lte': price_level}
        }

        # Merge additional filters
        if additional_filters:
            query_filter.update(additional_filters)

        # Execute query
        cursor = collection.find(
            query_filter,
            {'_id': 1, 'name': 1, 'has_surge_price': 1, 'priority': 1}
        ).sort('priority', -1)

        # Convert to list
        results = list(cursor)

        # Convert ObjectId to string
        for item in results:
            if '_id' in item:
                item['id'] = str(item.pop('_id'))

        return results

    except Exception as e:
        print(f"Error in query_places_geospatial: {str(e)}")
        return []

    finally:
        client.close()

# MAIN VIEW FUNCTIONS
@csrf_exempt
@require_http_methods(["POST"])
def create_travel_plan(request):
    """
    API endpoint để tạo kế hoạch du lịch

    POST /plan/

    Input (JSON):
        Required:
            - budget (float): Tổng ngân sách
            - num_people (int): Số người
            - area (string): Khu vực
            - departure_date (string): Ngày đi (YYYY-MM-DD)
            - return_date (string): Ngày về (YYYY-MM-DD)
        Optional:
            - location (string): Địa điểm cụ thể
            - travel_style (int|list): Phong cách du lịch
            - food_type (int|list): Loại ẩm thực
            - accommodation_type (int|list): Loại chỗ ở

    Output (JSON):
        {
            'success': bool,
            'budget_breakdown': dict,
            'schedule': list,
            'hotel_id': str,
            'alternatives': dict,
            'can_change': bool
        }
    """
    try:
        # Parse request body
        data = json.loads(request.body)

        # VALIDATION
        required_fields = ['budget', 'num_people', 'area', 'departure_date', 'return_date']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'message': f'Thiếu trường bắt buộc: {field}'
                }, status=400)

        # Convert date strings to date objects
        try:
            departure_date = datetime.strptime(data['departure_date'], '%Y-%m-%d').date()
            return_date = datetime.strptime(data['return_date'], '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Định dạng ngày không hợp lệ. Vui lòng sử dụng YYYY-MM-DD'
            }, status=400)

        # Validate dates
        if departure_date >= return_date:
            return JsonResponse({
                'success': False,
                'message': 'Ngày về phải sau ngày đi'
            }, status=400)

        # Validate num_people and budget
        if data['num_people'] <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Số người phải lớn hơn 0'
            }, status=400)

        if data['budget'] <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Ngân sách phải lớn hơn 0'
            }, status=400)

        # PROCESS INPUT
        budget = float(data['budget'])
        num_people = int(data['num_people'])
        area = data['area']

        # Optional fields
        location = data.get('location', None)
        travel_style = data.get('travel_style', None)
        food_type = data.get('food_type', None)
        accommodation_type = data.get('accommodation_type', None)

        # Tính số ngày
        num_days = (return_date - departure_date).days + 1

        # Phân chia ngân sách
        budget_info = calculate_budget_breakdown(budget, num_people, num_days)

        # Tính price level cho từng loại
        food_price_level = calculate_price_level(budget_info['food_per_meal'])
        hotel_price_level = calculate_price_level(budget_info['hotel_per_night'])
        other_price_level = calculate_price_level(budget_info['other_per_day'])

        # GET CENTER LOCATION
        search_term = None

        # Ưu tiên location nếu có, không thì dùng area
        if location:
            search_term = remove_vietnamese_accents(location)
        else:
            search_term = remove_vietnamese_accents(area)

        # Tìm trong database
        try:
            location_obj = Location.objects.get(search_name=search_term)
            center_coords = location_obj.coordinate['coordinates']
            search_radius = location_obj.suggested_radius
        except Location.DoesNotExist:
            # Tìm các địa điểm tương tự
            suggestions = find_similar_locations(search_term)

            return JsonResponse({
                'success': False,
                'message': f"Không tìm thấy địa điểm '{location or area}'. Có phải bạn muốn tìm:",
                'suggestions': suggestions
            })
        except Location.MultipleObjectsReturned:
            # Nếu có nhiều kết quả, lấy cái đầu tiên
            location_obj = Location.objects.filter(search_name=search_term).first()
            center_coords = location_obj.coordinate['coordinates']
            search_radius = location_obj.suggested_radius

        # FILTER RESTAURANTS
        restaurants = {'breakfast': [], 'lunch': [], 'dinner': []}

        # Build additional filters for restaurants
        rest_filters = {}
        if food_type:
            # Ensure it's a list
            if not isinstance(food_type, list):
                food_type = [food_type]
            rest_filters['cuisine_types'] = {'$in': food_type}

        # Query cho breakfast (active_hours chứa 0 hoặc 1)
        breakfast_filter = rest_filters.copy()
        breakfast_filter['active_hours'] = {'$in': [0, 1]}
        restaurants['breakfast'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            breakfast_filter
        )

        # Query cho lunch (active_hours chứa 0 hoặc 2)
        lunch_filter = rest_filters.copy()
        lunch_filter['active_hours'] = {'$in': [0, 2]}
        restaurants['lunch'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            lunch_filter
        )

        # Query cho dinner (active_hours chứa 0 hoặc 3)
        dinner_filter = rest_filters.copy()
        dinner_filter['active_hours'] = {'$in': [0, 3]}
        restaurants['dinner'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            dinner_filter
        )

        # FILTER HOTELS
        hotel_filters = {}
        if accommodation_type:
            # Ensure it's a list
            if not isinstance(accommodation_type, list):
                accommodation_type = [accommodation_type]
            hotel_filters['hotel_type'] = {'$in': accommodation_type}

        hotels = query_places_geospatial(
            'travel_hotel',
            center_coords,
            search_radius,
            hotel_price_level,
            hotel_filters
        )

        # Kiểm tra xem có hotel không
        if not hotels:
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy khách sạn phù hợp với ngân sách và yêu cầu của bạn.'
            })

        # FILTER ATTRACTIONS
        attraction_filters = {}
        if travel_style:
            # Ensure it's a list
            if not isinstance(travel_style, list):
                travel_style = [travel_style]
            attraction_filters['tags'] = {'$in': travel_style}

        attractions = query_places_geospatial(
            'travel_attraction',
            center_coords,
            search_radius,
            other_price_level,
            attraction_filters
        )

        # CREATE ITINERARY
        schedule = []

        # Chọn hotel (lấy cái đầu tiên có priority cao nhất)
        selected_hotel_id = str(hotels[0]['id']) if hotels else None

        # Indices để track vị trí đang dùng
        breakfast_idx = 0
        lunch_idx = 0
        dinner_idx = 0
        attraction_idx = 0

        # Số attraction mỗi ngày (mặc định 2)
        attractions_per_day = 2

        # Tạo lịch cho từng ngày
        for day_offset in range(num_days):
            current_date = departure_date + timedelta(days=day_offset)

            # Chọn các bữa ăn
            breakfast_id = None
            if breakfast_idx < len(restaurants['breakfast']):
                breakfast_id = str(restaurants['breakfast'][breakfast_idx]['id'])
                breakfast_idx += 1

            lunch_id = None
            if lunch_idx < len(restaurants['lunch']):
                lunch_id = str(restaurants['lunch'][lunch_idx]['id'])
                lunch_idx += 1

            dinner_id = None
            if dinner_idx < len(restaurants['dinner']):
                dinner_id = str(restaurants['dinner'][dinner_idx]['id'])
                dinner_idx += 1

            # Chọn các điểm tham quan
            places = []
            for _ in range(attractions_per_day):
                if attraction_idx < len(attractions):
                    places.append(str(attractions[attraction_idx]['id']))
                    attraction_idx += 1

            day_schedule = {
                'date': current_date.strftime('%Y-%m-%d'),
                'breakfast': breakfast_id,
                'lunch': lunch_id,
                'dinner': dinner_id,
                'places': places
            }

            schedule.append(day_schedule)

        # PREPARE ALTERNATIVES
        alternatives = {
            'breakfast': [str(r['id']) for r in restaurants['breakfast'][breakfast_idx:]],
            'lunch': [str(r['id']) for r in restaurants['lunch'][lunch_idx:]],
            'dinner': [str(r['id']) for r in restaurants['dinner'][dinner_idx:]],
            'hotels': [str(h['id']) for h in hotels[1:]],
            'attractions': [str(a['id']) for a in attractions[attraction_idx:]]
        }

        # PREPARE OUTPUT
        result = {
            'success': True,
            'budget_breakdown': {
                'food': budget_info['food_budget'],
                'hotel': budget_info['hotel_budget'],
                'other': budget_info['other_budget']
            },
            'schedule': schedule,
            'hotel_id': selected_hotel_id,
            'alternatives': alternatives,
            'can_change': True
        }

        # SAVE TO DATABASE (if user authenticated)
        if request.user.is_authenticated:
            try:
                # Save input
                travel_input = TravelInput.objects.create(
                    budget=budget,
                    num_people=num_people,
                    area=area,
                    departure_date=departure_date,
                    return_date=return_date,
                    location=location,
                    travel_style=travel_style if isinstance(travel_style, int) else None,
                    food_type=food_type if isinstance(food_type, int) else None,
                    accommodation_type=accommodation_type if isinstance(accommodation_type, int) else None
                )

                # Save output
                TravelOutput.objects.create(
                    user=request.user,
                    input_id=str(travel_input.id),
                    summary_info={
                        'hotel_id': selected_hotel_id,
                        'budget_breakdown': result['budget_breakdown'],
                        'location': location_obj.name  # Thêm location để hiển thị trong lịch sử
                    },
                    itinerary=schedule
                )
            except Exception as e:
                # Log error but still return the result
                print(f"Error saving travel plan: {str(e)}")

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_areas(request):
    """
    GET /areas/
    API lay danh sach cac area kem id de lap ke hoach
    """
    try:
        locations = Location.objects.all()
        area_list = tuple({loc.name: loc.id} for loc in locations)
        return JsonResponse({"area": area_list})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# HISTORY & PLAN DETAIL VIEWS
@csrf_exempt
@require_http_methods(["GET"])
def get_travel_history(request):
    """
    GET /history/

    Lấy lịch sử kế hoạch của user

    Output:
        {
            'success': bool,
            'data': [
                {
                    'id': str,
                    'created_at': str,
                    'location': str (từ summary_info)
                }
            ]
        }
    """
    try:
        # Kiểm tra user đã đăng nhập chưa
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Bạn cần đăng nhập để xem lịch sử'
            }, status=401)

        # Lấy tất cả kế hoạch của user, sắp xếp từ mới đến cũ
        travel_outputs = TravelOutput.objects.filter(
            user=request.user
        ).order_by('-created_at')

        # Chuẩn bị dữ liệu trả về
        history_list = []
        for output in travel_outputs:
            history_item = {
                'id': str(output.id),
                'created_at': output.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'location': output.summary_info.get('location', 'N/A')
            }
            history_list.append(history_item)

        return JsonResponse({
            'success': True,
            'data': history_list
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def view_plan_detail(request, plan_id):
    """
    GET /plan/<plan_id>/

    Xem chi tiết kế hoạch (không có list phụ lục)

    Output:
        {
            'success': bool,
            'budget_breakdown': dict,
            'schedule': list,
            'hotel_id': str,
            'can_change': False
        }
    """
    try:
        # Lấy kế hoạch từ database
        try:
            travel_output = TravelOutput.objects.get(id=plan_id)
        except TravelOutput.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy kế hoạch'
            }, status=404)

        # Kiểm tra quyền truy cập (chỉ user tạo mới được xem)
        if request.user.is_authenticated and travel_output.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Bạn không có quyền xem kế hoạch này'
            }, status=403)

        # Chuẩn bị output
        result = {
            'success': True,
            'budget_breakdown': travel_output.summary_info.get('budget_breakdown', {}),
            'schedule': travel_output.itinerary,
            'hotel_id': travel_output.summary_info.get('hotel_id'),
            'can_change': False
        }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def edit_plan(request, plan_id):
    """
    GET /plan/<plan_id>/edit/

    Chỉnh sửa kế hoạch (có list phụ lục để thay đổi)

    Output:
        {
            'success': bool,
            'budget_breakdown': dict,
            'schedule': list,
            'hotel_id': str,
            'alternatives': dict,
            'can_change': True
        }
    """
    try:
        # Lấy kế hoạch từ database
        try:
            travel_output = TravelOutput.objects.get(id=plan_id)
        except TravelOutput.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy kế hoạch'
            }, status=404)

        # Kiểm tra quyền truy cập
        if not request.user.is_authenticated or travel_output.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Bạn không có quyền chỉnh sửa kế hoạch này'
            }, status=403)

        # Lấy input gốc từ input_id
        try:
            travel_input = TravelInput.objects.get(id=travel_output.input_id)
        except TravelInput.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy thông tin input gốc'
            }, status=404)

        # TÁI SỬ DỤNG LOGIC TỪ create_travel_plan

        # Lấy thông tin từ input
        budget = float(travel_input.budget)
        num_people = travel_input.num_people
        area = travel_input.area
        location = travel_input.location
        travel_style = travel_input.travel_style
        food_type = travel_input.food_type
        accommodation_type = travel_input.accommodation_type

        # Tính số ngày
        num_days = (travel_input.return_date - travel_input.departure_date).days + 1

        # Phân chia ngân sách
        budget_info = calculate_budget_breakdown(budget, num_people, num_days)

        # Tính price level
        food_price_level = calculate_price_level(budget_info['food_per_meal'])
        hotel_price_level = calculate_price_level(budget_info['hotel_per_night'])
        other_price_level = calculate_price_level(budget_info['other_per_day'])

        # GET CENTER LOCATION
        search_term = None
        if location:
            search_term = remove_vietnamese_accents(location)
        else:
            search_term = remove_vietnamese_accents(area)

        try:
            location_obj = Location.objects.get(search_name=search_term)
            center_coords = location_obj.coordinate['coordinates']
            search_radius = location_obj.suggested_radius
        except Location.DoesNotExist:
            suggestions = find_similar_locations(search_term)
            return JsonResponse({
                'success': False,
                'message': f"Không tìm thấy địa điểm '{location or area}'",
                'suggestions': suggestions
            })
        except Location.MultipleObjectsReturned:
            location_obj = Location.objects.filter(search_name=search_term).first()
            center_coords = location_obj.coordinate['coordinates']
            search_radius = location_obj.suggested_radius

        # FILTER RESTAURANTS
        restaurants = {'breakfast': [], 'lunch': [], 'dinner': []}

        rest_filters = {}
        if food_type:
            if not isinstance(food_type, list):
                food_type = [food_type]
            rest_filters['cuisine_types'] = {'$in': food_type}

        # Query breakfast
        breakfast_filter = rest_filters.copy()
        breakfast_filter['active_hours'] = {'$in': [0, 1]}
        restaurants['breakfast'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            breakfast_filter
        )

        # Query lunch
        lunch_filter = rest_filters.copy()
        lunch_filter['active_hours'] = {'$in': [0, 2]}
        restaurants['lunch'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            lunch_filter
        )

        # Query dinner
        dinner_filter = rest_filters.copy()
        dinner_filter['active_hours'] = {'$in': [0, 3]}
        restaurants['dinner'] = query_places_geospatial(
            'travel_restaurant',
            center_coords,
            search_radius,
            food_price_level,
            dinner_filter
        )

        # FILTER HOTELS
        hotel_filters = {}
        if accommodation_type:
            if not isinstance(accommodation_type, list):
                accommodation_type = [accommodation_type]
            hotel_filters['hotel_type'] = {'$in': accommodation_type}

        hotels = query_places_geospatial(
            'travel_hotel',
            center_coords,
            search_radius,
            hotel_price_level,
            hotel_filters
        )

        # FILTER ATTRACTIONS
        attraction_filters = {}
        if travel_style:
            if not isinstance(travel_style, list):
                travel_style = [travel_style]
            attraction_filters['tags'] = {'$in': travel_style}

        attractions = query_places_geospatial(
            'travel_attraction',
            center_coords,
            search_radius,
            other_price_level,
            attraction_filters
        )

        # PREPARE ALTERNATIVES
        # Lấy toàn bộ list để làm alternatives (không cần tạo lại schedule)
        alternatives = {
            'breakfast': [str(r['id']) for r in restaurants['breakfast']],
            'lunch': [str(r['id']) for r in restaurants['lunch']],
            'dinner': [str(r['id']) for r in restaurants['dinner']],
            'hotels': [str(h['id']) for h in hotels],
            'attractions': [str(a['id']) for a in attractions]
        }

        # PREPARE OUTPUT
        result = {
            'success': True,
            'budget_breakdown': travel_output.summary_info.get('budget_breakdown', {}),
            'schedule': travel_output.itinerary,
            'hotel_id': travel_output.summary_info.get('hotel_id'),
            'alternatives': alternatives,
            'can_change': True
        }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=500)
