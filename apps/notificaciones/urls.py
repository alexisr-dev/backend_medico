from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificacionViewSet, RecordatorioViewSet

router = DefaultRouter()
router.register("recordatorios", RecordatorioViewSet, basename="recordatorio")
router.register("", NotificacionViewSet, basename="notificacion")

urlpatterns = [path("", include(router.urls))]
