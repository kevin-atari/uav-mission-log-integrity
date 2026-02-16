from django.contrib import admin
from django.urls import path
from storage.views import home, flights_page, flight_versions_page

urlpatterns = [
    path("", home, name="home"),
    path("flights/", flights_page, name="flights_page"),
    path("flights/<str:flight_id>/", flight_versions_page, name="flight_versions_page"),
    path("admin/", admin.site.urls),
]
