from django.urls import path

from .views import (
    CitasPorDiaView,
    DemandaEspecialidadView,
    DisponibilidadGlobalView,
    IndicadoresGeneralesView,
    NoAsistenciaView,
    OcupacionDoctoresView,
)

urlpatterns = [
    path("ocupacion/", OcupacionDoctoresView.as_view(), name="reporte_ocupacion"),
    path("no-asistencia/", NoAsistenciaView.as_view(), name="reporte_no_asistencia"),
    path("citas-por-dia/", CitasPorDiaView.as_view(), name="reporte_citas_por_dia"),
    path("demanda-especialidad/", DemandaEspecialidadView.as_view(), name="reporte_demanda"),
    path("disponibilidad/", DisponibilidadGlobalView.as_view(), name="reporte_disponibilidad"),
    path("indicadores/", IndicadoresGeneralesView.as_view(), name="reporte_indicadores"),
]
