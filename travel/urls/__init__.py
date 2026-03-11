from django.urls import path, include

urlpatterns = [
    path("", include("travel.urls.travel_urls")),
    # path("places/", include("travel.urls.place_urls")),
]