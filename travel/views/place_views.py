from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from django.conf import settings
import json

from ..models import Restaurant, Hotel, Attraction, Location
from ..serializers import RestaurantSerializer, HotelSerializer, AttractionSerializer, LocationSerializer


def get_mongodb_collection(collection_name):
    """
    Lấy MongoDB collection

    Args:
        collection_name (str): Tên collection

    Returns:
        collection: MongoDB collection object
    """
    db_settings = settings.DATABASES['default']
    host = db_settings.get('CLIENT', {}).get('host', 'mongodb://localhost:27017/')

    client = MongoClient(host)
    db = client[db_settings['NAME']]

    return db[collection_name], client


def convert_objectid_to_string(results):
    """
    Convert MongoDB ObjectId to string trong results

    Args:
        results (list): Danh sách kết quả từ MongoDB

    Returns:
        list: Kết quả với _id đã convert sang string
    """
    for item in results:
        if '_id' in item:
            item['id'] = str(item['_id'])
            del item['_id']
    return results


# RESTAURANT VIEWS
@api_view(['GET'])
def list_restaurants(request):
    """
    GET /places/restaurants/

    Lấy danh sách nhà hàng với filter options

    Query Parameters:
        - cuisine_types: int hoặc comma-separated (vd: 1 hoặc 1,2,3)
        - price_level: int (1-5)
        - min_rating: float (0-5)
        - active_hours: int (0: cả ngày, 1: sáng, 2: trưa, 3: tối)
        - location: string (search_name của Location)
        - radius: int (meters, default: 5000)
        - limit: int (số lượng kết quả, default: 20)
        - offset: int (pagination offset, default: 0)
    """
    try:
        # Build filters
        filters = {}

        # Filter by cuisine_types
        if request.GET.get('cuisine_types'):
            cuisine_types_str = request.GET.get('cuisine_types')
            if ',' in cuisine_types_str:
                cuisine_types = [int(x.strip()) for x in cuisine_types_str.split(',')]
            else:
                cuisine_types = [int(cuisine_types_str)]
            filters['cuisine_types'] = {'$in': cuisine_types}

        # Filter by price_level
        if request.GET.get('price_level'):
            filters['price_level'] = {'$lte': int(request.GET.get('price_level'))}

        # Filter by min_rating
        if request.GET.get('min_rating'):
            filters['rating'] = {'$gte': float(request.GET.get('min_rating'))}

        # Filter by active_hours
        if request.GET.get('active_hours'):
            active_hours = int(request.GET.get('active_hours'))
            filters['active_hours'] = {'$in': [0, active_hours]}

        # Geospatial filter by location
        if request.GET.get('location'):
            location_name = request.GET.get('location')
            try:
                location_obj = Location.objects.get(search_name=location_name.lower())
                center_coords = location_obj.coordinate['coordinates']
                radius = int(request.GET.get('radius', location_obj.suggested_radius))

                filters['location'] = {
                    '$near': {
                        '$geometry': {
                            'type': 'Point',
                            'coordinates': center_coords
                        },
                        '$maxDistance': radius
                    }
                }
            except Location.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Không tìm thấy địa điểm: {location_name}'
                }, status=status.HTTP_404_NOT_FOUND)

        # Pagination
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        # Query MongoDB
        collection, client = get_mongodb_collection('travel_restaurant')

        try:
            cursor = collection.find(filters).sort('priority', -1).skip(offset).limit(limit)
            results = list(cursor)
            total_count = collection.count_documents(filters)

            # Convert ObjectId to string
            results = convert_objectid_to_string(results)

            return Response({
                'success': True,
                'data': results,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
        finally:
            client.close()

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_restaurant_detail(request, restaurant_id):
    """
    GET /places/restaurants/<id>/

    Lấy chi tiết một nhà hàng
    """
    try:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        serializer = RestaurantSerializer(restaurant)

        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# HOTEL VIEWS
@api_view(['GET'])
def list_hotels(request):
    """
    GET /places/hotels/

    Lấy danh sách khách sạn với filter options

    Query Parameters:
        - hotel_type: int hoặc comma-separated
        - price_level: int (1-5)
        - min_rating: float (0-5)
        - location: string (search_name của Location)
        - radius: int (meters, default: 5000)
        - limit: int (default: 20)
        - offset: int (default: 0)
    """
    try:
        # Build filters
        filters = {}

        # Filter by hotel_type
        if request.GET.get('hotel_type'):
            hotel_type_str = request.GET.get('hotel_type')
            if ',' in hotel_type_str:
                hotel_types = [int(x.strip()) for x in hotel_type_str.split(',')]
            else:
                hotel_types = [int(hotel_type_str)]
            filters['hotel_type'] = {'$in': hotel_types}

        # Filter by price_level
        if request.GET.get('price_level'):
            filters['price_level'] = {'$lte': int(request.GET.get('price_level'))}

        # Filter by min_rating
        if request.GET.get('min_rating'):
            filters['rating'] = {'$gte': float(request.GET.get('min_rating'))}

        # Geospatial filter by location
        if request.GET.get('location'):
            location_name = request.GET.get('location')
            try:
                location_obj = Location.objects.get(search_name=location_name.lower())
                center_coords = location_obj.coordinate['coordinates']
                radius = int(request.GET.get('radius', location_obj.suggested_radius))

                filters['location'] = {
                    '$near': {
                        '$geometry': {
                            'type': 'Point',
                            'coordinates': center_coords
                        },
                        '$maxDistance': radius
                    }
                }
            except Location.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Không tìm thấy địa điểm: {location_name}'
                }, status=status.HTTP_404_NOT_FOUND)

        # Pagination
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        # Query MongoDB
        collection, client = get_mongodb_collection('travel_hotel')

        try:
            cursor = collection.find(filters).sort('priority', -1).skip(offset).limit(limit)
            results = list(cursor)
            total_count = collection.count_documents(filters)

            # Convert ObjectId to string
            results = convert_objectid_to_string(results)

            return Response({
                'success': True,
                'data': results,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
        finally:
            client.close()

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_hotel_detail(request, hotel_id):
    """
    GET /places/hotels/<id>/

    Lấy chi tiết một khách sạn
    """
    try:
        hotel = get_object_or_404(Hotel, id=hotel_id)
        serializer = HotelSerializer(hotel)

        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ATTRACTION VIEWS
@api_view(['GET'])
def list_attractions(request):
    """
    GET /places/attractions/

    Lấy danh sách điểm tham quan với filter options

    Query Parameters:
        - tags: int hoặc comma-separated (travel_style tags)
        - price_level: int (1-5)
        - min_rating: float (0-5)
        - location: string (search_name của Location)
        - radius: int (meters, default: 5000)
        - limit: int (default: 20)
        - offset: int (default: 0)
    """
    try:
        # Build filters
        filters = {}

        # Filter by tags
        if request.GET.get('tags'):
            tags_str = request.GET.get('tags')
            if ',' in tags_str:
                tags = [int(x.strip()) for x in tags_str.split(',')]
            else:
                tags = [int(tags_str)]
            filters['tags'] = {'$in': tags}

        # Filter by price_level
        if request.GET.get('price_level'):
            filters['price_level'] = {'$lte': int(request.GET.get('price_level'))}

        # Filter by min_rating
        if request.GET.get('min_rating'):
            filters['rating'] = {'$gte': float(request.GET.get('min_rating'))}

        # Geospatial filter by location
        if request.GET.get('location'):
            location_name = request.GET.get('location')
            try:
                location_obj = Location.objects.get(search_name=location_name.lower())
                center_coords = location_obj.coordinate['coordinates']
                radius = int(request.GET.get('radius', location_obj.suggested_radius))

                filters['location'] = {
                    '$near': {
                        '$geometry': {
                            'type': 'Point',
                            'coordinates': center_coords
                        },
                        '$maxDistance': radius
                    }
                }
            except Location.DoesNotExist:
                return Response({
                    'success': False,
                    'message': f'Không tìm thấy địa điểm: {location_name}'
                }, status=status.HTTP_404_NOT_FOUND)

        # Pagination
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        # Query MongoDB
        collection, client = get_mongodb_collection('travel_attraction')

        try:
            cursor = collection.find(filters).sort('priority', -1).skip(offset).limit(limit)
            results = list(cursor)
            total_count = collection.count_documents(filters)

            # Convert ObjectId to string
            results = convert_objectid_to_string(results)

            return Response({
                'success': True,
                'data': results,
                'total': total_count,
                'limit': limit,
                'offset': offset
            })
        finally:
            client.close()

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_attraction_detail(request, attraction_id):
    """
    GET /places/attractions/<id>/

    Lấy chi tiết một điểm tham quan
    """
    try:
        attraction = get_object_or_404(Attraction, id=attraction_id)
        serializer = AttractionSerializer(attraction)

        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# SEARCH & LOCATION VIEWS
@api_view(['GET'])
def search_places(request):
    """
    GET /places/search/

    Tìm kiếm tất cả các loại địa điểm theo tên

    Query Parameters:
        - q: string (search query)
        - types: string (comma-separated: restaurant,hotel,attraction, default: all)
        - limit: int (default: 10)
    """
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({
                'success': False,
                'message': 'Thiếu từ khóa tìm kiếm (q)'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine which types to search
        types_str = request.GET.get('types', 'restaurant,hotel,attraction')
        search_types = [t.strip() for t in types_str.split(',')]

        limit = int(request.GET.get('limit', 10))

        results = {
            'restaurants': [],
            'hotels': [],
            'attractions': []
        }

        # Create regex pattern for case-insensitive search
        search_pattern = {'$regex': query, '$options': 'i'}

        # Search restaurants
        if 'restaurant' in search_types:
            collection, client = get_mongodb_collection('travel_restaurant')
            try:
                cursor = collection.find(
                    {'name': search_pattern}
                ).sort('priority', -1).limit(limit)
                restaurants = list(cursor)
                results['restaurants'] = convert_objectid_to_string(restaurants)
            finally:
                client.close()

        # Search hotels
        if 'hotel' in search_types:
            collection, client = get_mongodb_collection('travel_hotel')
            try:
                cursor = collection.find(
                    {'name': search_pattern}
                ).sort('priority', -1).limit(limit)
                hotels = list(cursor)
                results['hotels'] = convert_objectid_to_string(hotels)
            finally:
                client.close()

        # Search attractions
        if 'attraction' in search_types:
            collection, client = get_mongodb_collection('travel_attraction')
            try:
                cursor = collection.find(
                    {'name': search_pattern}
                ).sort('priority', -1).limit(limit)
                attractions = list(cursor)
                results['attractions'] = convert_objectid_to_string(attractions)
            finally:
                client.close()

        return Response({
            'success': True,
            'query': query,
            'results': results
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_places_near_location(request):
    """
    GET /places/nearby/

    Lấy tất cả các địa điểm gần một location

    Query Parameters:
        - location: string (search_name của Location) - required
        - radius: int (meters, default: from location.suggested_radius)
        - types: string (comma-separated: restaurant,hotel,attraction, default: all)
        - limit: int (số lượng mỗi loại, default: 10)
    """
    try:
        location_name = request.GET.get('location', '').strip()
        if not location_name:
            return Response({
                'success': False,
                'message': 'Thiếu tham số location'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get location
        try:
            location_obj = Location.objects.get(search_name=location_name.lower())
            center_coords = location_obj.coordinate['coordinates']
            radius = int(request.GET.get('radius', location_obj.suggested_radius))
        except Location.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Không tìm thấy địa điểm: {location_name}'
            }, status=status.HTTP_404_NOT_FOUND)

        # Determine which types to search
        types_str = request.GET.get('types', 'restaurant,hotel,attraction')
        search_types = [t.strip() for t in types_str.split(',')]

        limit = int(request.GET.get('limit', 10))

        results = {
            'location': {
                'name': location_obj.name,
                'search_name': location_obj.search_name,
                'coordinates': center_coords,
                'radius': radius
            },
            'restaurants': [],
            'hotels': [],
            'attractions': []
        }

        # Geospatial filter
        geo_filter = {
            'location': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': center_coords
                    },
                    '$maxDistance': radius
                }
            }
        }

        # Get restaurants nearby
        if 'restaurant' in search_types:
            collection, client = get_mongodb_collection('travel_restaurant')
            try:
                cursor = collection.find(geo_filter).limit(limit)
                restaurants = list(cursor)
                results['restaurants'] = convert_objectid_to_string(restaurants)
            finally:
                client.close()

        # Get hotels nearby
        if 'hotel' in search_types:
            collection, client = get_mongodb_collection('travel_hotel')
            try:
                cursor = collection.find(geo_filter).limit(limit)
                hotels = list(cursor)
                results['hotels'] = convert_objectid_to_string(hotels)
            finally:
                client.close()

        # Get attractions nearby
        if 'attraction' in search_types:
            collection, client = get_mongodb_collection('travel_attraction')
            try:
                cursor = collection.find(geo_filter).limit(limit)
                attractions = list(cursor)
                results['attractions'] = convert_objectid_to_string(attractions)
            finally:
                client.close()

        return Response({
            'success': True,
            'data': results
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# LOCATION VIEWS
@api_view(['GET'])
def list_locations(request):
    """
    GET /places/locations/

    Lấy danh sách các địa điểm trong hệ thống
    """
    try:
        locations = Location.objects.all()
        serializer = LocationSerializer(locations, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_location_detail(request, location_id):
    """
    GET /places/locations/<id>/

    Lấy chi tiết một địa điểm
    """
    try:
        location = get_object_or_404(Location, id=location_id)
        serializer = LocationSerializer(location)

        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# LIST PLACES (Special Logic)
@api_view(['GET'])
def list_places_for_browse(request):
    """
    GET /places/browse/

    List địa điểm với logic đặc biệt:
    - Lần đầu (không có filter): lấy ngẫu nhiên 12 object mỗi loại (Hotels, Restaurants, Attractions)
      Output: {"Hotels": [...], "Restaurants": [...], "Attractions": [...]}
    - Lần sau (có filter): lọc theo option, mỗi lần chỉ 1 loại, lấy 12 objects
      Output: {"Hotels": [...]} hoặc {"Restaurants": [...]} hoặc {"Attractions": [...]}

    Query Parameters:
        - travel_style: int (cho Attractions)
        - food_type: int (cho Restaurants)
        - accommodation_type: int (cho Hotels)

    Chỉ lấy: id, name, address, rating, price_level
    """
    try:
        # Kiểm tra xem có filter hay không
        has_filter = any([
            request.GET.get('travel_style'),
            request.GET.get('food_type'),
            request.GET.get('accommodation_type')
        ])

        result = {}
        limit = 12

        # Fields cần lấy (chỉ lấy những field cần thiết)
        projection = {
            '_id': 1,
            'name': 1,
            'address': 1,
            'rating': 1,
            'price_level': 1
        }

        if not has_filter:
            # LẦN ĐẦU: Lấy ngẫu nhiên 12 object mỗi loại

            # Lấy Restaurants
            collection, client = get_mongodb_collection('travel_restaurant')
            try:
                # Sử dụng $sample để lấy ngẫu nhiên
                pipeline = [
                    {'$sample': {'size': limit}},
                    {'$project': projection}
                ]
                restaurants = list(collection.aggregate(pipeline))
                result['Restaurants'] = convert_objectid_to_string(restaurants)
            finally:
                client.close()

            # Lấy Hotels
            collection, client = get_mongodb_collection('travel_hotel')
            try:
                pipeline = [
                    {'$sample': {'size': limit}},
                    {'$project': projection}
                ]
                hotels = list(collection.aggregate(pipeline))
                result['Hotels'] = convert_objectid_to_string(hotels)
            finally:
                client.close()

            # Lấy Attractions
            collection, client = get_mongodb_collection('travel_attraction')
            try:
                pipeline = [
                    {'$sample': {'size': limit}},
                    {'$project': projection}
                ]
                attractions = list(collection.aggregate(pipeline))
                result['Attractions'] = convert_objectid_to_string(attractions)
            finally:
                client.close()

        else:
            # NHỮNG LẦN SAU: Lọc theo option, mỗi lần 1 loại

            # Lọc Restaurants theo food_type
            if request.GET.get('food_type'):
                food_type = int(request.GET.get('food_type'))
                collection, client = get_mongodb_collection('travel_restaurant')
                try:
                    cursor = collection.find(
                        {'cuisine_types': food_type},
                        projection
                    ).sort('priority', -1).limit(limit)
                    restaurants = list(cursor)
                    result['Restaurants'] = convert_objectid_to_string(restaurants)
                finally:
                    client.close()

            # Lọc Hotels theo accommodation_type
            elif request.GET.get('accommodation_type'):
                accommodation_type = int(request.GET.get('accommodation_type'))
                collection, client = get_mongodb_collection('travel_hotel')
                try:
                    cursor = collection.find(
                        {'hotel_type': accommodation_type},
                        projection
                    ).sort('priority', -1).limit(limit)
                    hotels = list(cursor)
                    result['Hotels'] = convert_objectid_to_string(hotels)
                finally:
                    client.close()

            # Lọc Attractions theo travel_style
            elif request.GET.get('travel_style'):
                travel_style = int(request.GET.get('travel_style'))
                collection, client = get_mongodb_collection('travel_attraction')
                try:
                    cursor = collection.find(
                        {'tags': travel_style},
                        projection
                    ).sort('priority', -1).limit(limit)
                    attractions = list(cursor)
                    result['Attractions'] = convert_objectid_to_string(attractions)
                finally:
                    client.close()

        return Response({
            'success': True,
            'data': result
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_place_detail_universal(request, place_id):
    """
    GET /places/<id>/

    Lấy chi tiết một địa điểm (tự động detect loại: restaurant/hotel/attraction)

    Dùng cho chức năng 6: Thông tin chi tiết
    """
    try:
        # Thử tìm trong Restaurant
        try:
            restaurant = Restaurant.objects.get(id=place_id)
            serializer = RestaurantSerializer(restaurant)
            return Response({
                'success': True,
                'type': 'restaurant',
                'data': serializer.data
            })
        except Restaurant.DoesNotExist:
            pass

        # Thử tìm trong Hotel
        try:
            hotel = Hotel.objects.get(id=place_id)
            serializer = HotelSerializer(hotel)
            return Response({
                'success': True,
                'type': 'hotel',
                'data': serializer.data
            })
        except Hotel.DoesNotExist:
            pass

        # Thử tìm trong Attraction
        try:
            attraction = Attraction.objects.get(id=place_id)
            serializer = AttractionSerializer(attraction)
            return Response({
                'success': True,
                'type': 'attraction',
                'data': serializer.data
            })
        except Attraction.DoesNotExist:
            pass

        # Không tìm thấy
        return Response({
            'success': False,
            'message': 'Không tìm thấy địa điểm'
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
