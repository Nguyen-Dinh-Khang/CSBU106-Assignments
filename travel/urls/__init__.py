from django.urls import path, include

urlpatterns = [
    path("travel/", include("travel.urls.travel_urls")),
    # path("places/", include("travel.urls.place_urls")),
]