from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('locations/search/', views.location_search, name='location-search'),
    path('locations/<str:location_id>/', views.location_detail, name='location-detail'),
    path('routes/analyze/', views.analyze, name='analyze'),
    path('routes/demo/', views.demo, name='demo'),
    path('routes/<str:route_id>/', views.route_detail, name='route-detail'),
    path('routes/<str:route_id>/checkpoints/', views.route_checkpoints, name='route-checkpoints'),
    path('analyses/<str:analysis_id>/forecast/', views.analysis_forecast, name='analysis-forecast'),
]
