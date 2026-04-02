from django.urls import path
from ..views.trip_views import (
    create_travel_plan,
    get_areas,
    get_travel_history,
    view_plan_detail,
    edit_plan
)
from ..views import place_views

urlpatterns = [
    # Travel planning API
    path('plan/', create_travel_plan, name='create_travel_plan'),
    path('areas/', get_areas, name='get_areas'),

    # Travel history and plan details
    path('history/', get_travel_history, name='get_travel_history'),
    path('plan/<str:plan_id>/', view_plan_detail, name='view_plan_detail'),
    path('plan/<str:plan_id>/edit/', edit_plan, name='edit_plan'),

    # Place browsing (special logic for listing)
    path('places/browse/', place_views.list_places_for_browse, name='browse_places'),

    # Universal place detail endpoint
    path('places/<str:place_id>/', place_views.get_place_detail_universal, name='place_detail_universal'),

    # Restaurant endpoints
    path('places/restaurants/', place_views.list_restaurants, name='list_restaurants'),
    path('places/restaurants/<str:restaurant_id>/', place_views.get_restaurant_detail, name='restaurant_detail'),

    # Hotel endpoints
    path('places/hotels/', place_views.list_hotels, name='list_hotels'),
    path('places/hotels/<str:hotel_id>/', place_views.get_hotel_detail, name='hotel_detail'),

    # Attraction endpoints
    path('places/attractions/', place_views.list_attractions, name='list_attractions'),
    path('places/attractions/<str:attraction_id>/', place_views.get_attraction_detail, name='attraction_detail'),

    # Search & nearby
    path('places/search/', place_views.search_places, name='search_places'),
    path('places/nearby/', place_views.get_places_near_location, name='places_nearby'),

    # Location endpoints
    path('places/locations/', place_views.list_locations, name='list_locations'),
    path('places/locations/<str:location_id>/', place_views.get_location_detail, name='location_detail'),
]
