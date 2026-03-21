from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import *


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]


# router = DefaultRouter()
# # Đăng ký các ViewSet cho Hotel, Restaurant, Attraction
# router.register(r'hotels', views.HotelViewSet, basename='hotel')
# router.register(r'restaurants', views.RestaurantViewSet, basename='restaurant')
# router.register(r'attractions', views.AttractionViewSet, basename='attraction')
# # router.register(r'hotels', ...): này là tạo một lúc 5 cái Get, Put, Post,...

# urlpatterns = [
#     path('', include(router.urls)),
#     # Nếu sau này bạn có hàm lọc cực khó (không dùng ViewSet), bạn sẽ thêm ở đây:
#     # path('complex-filter/', views.ComplexFilterView.as_view()),
# ]