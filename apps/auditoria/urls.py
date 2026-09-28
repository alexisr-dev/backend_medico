from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AuditoriaAccesoViewSet

router = DefaultRouter()
router.register("", AuditoriaAccesoViewSet, basename="auditoria")

urlpatterns = [path("", include(router.urls))]
