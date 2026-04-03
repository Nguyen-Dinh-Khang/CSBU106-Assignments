from django.urls import path, include
from rest_framework.routers import DefaultRouter

from ..views.trip_views import (
    CreateTravelPlanView,
    GetAreasView,
    GetTravelHistoryView,
    ViewPlanDetailView,
    EditPlanView
)
from ..views.place_views import (
    PlaceBrowseView,
    PlaceDetailUniversalView,
    RestaurantViewSet,
    HotelViewSet,
    AttractionViewSet
)

router = DefaultRouter()
router.register(r'places/restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'places/hotels', HotelViewSet, basename='hotel')
router.register(r'places/attractions', AttractionViewSet, basename='attraction')

urlpatterns = [
    # Travel planning API
    path('plan/', CreateTravelPlanView.as_view(), name='create_travel_plan'),
    path('areas/', GetAreasView.as_view(), name='get_areas'),

    # Travel history and plan details
    path('history/', GetTravelHistoryView.as_view(), name='get_travel_history'),
    path('plan/<str:plan_id>/', ViewPlanDetailView.as_view(), name='view_plan_detail'),
    path('plan/<str:plan_id>/edit/', EditPlanView.as_view(), name='edit_plan'),

    # Place browsing
    path('places/browse/', PlaceBrowseView.as_view(), name='browse_places'),
    path('places/<str:place_id>/', PlaceDetailUniversalView.as_view(), name='place_detail_universal'),

    path('', include(router.urls)),
]
