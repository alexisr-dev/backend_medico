from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PacientePerfilViewSet

router = DefaultRouter()
router.register("", PacientePerfilViewSet, basename="paciente")

urlpatterns = [path("", include(router.urls))]
