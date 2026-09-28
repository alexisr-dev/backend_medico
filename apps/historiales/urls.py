from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ArchivoMedicoViewSet, HistorialMedicoViewSet, RecetaViewSet, RegistroConsultaViewSet

router = DefaultRouter()
router.register("consultas", RegistroConsultaViewSet, basename="registro_consulta")
router.register("recetas", RecetaViewSet, basename="receta")
router.register("archivos", ArchivoMedicoViewSet, basename="archivo_medico")
router.register("", HistorialMedicoViewSet, basename="historial")

urlpatterns = [path("", include(router.urls))]
