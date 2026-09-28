from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BloqueoHorarioViewSet,
    DisponibilidadHorariaViewSet,
    DoctorPerfilViewSet,
    EspecialidadViewSet,
)

router = DefaultRouter()
router.register("especialidades", EspecialidadViewSet, basename="especialidad")
router.register("disponibilidades", DisponibilidadHorariaViewSet, basename="disponibilidad")
router.register("bloqueos", BloqueoHorarioViewSet, basename="bloqueo")
router.register("", DoctorPerfilViewSet, basename="doctor")

urlpatterns = [path("", include(router.urls))]
