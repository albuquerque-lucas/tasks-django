from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PriorityLevelViewSet

router = DefaultRouter()
router.register(r'', PriorityLevelViewSet, basename='priority-level')

urlpatterns = [
    path('', include(router.urls)),
]
