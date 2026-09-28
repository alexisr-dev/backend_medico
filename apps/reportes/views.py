from datetime import date, timedelta

from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.permissions import EsAdmin, EsDoctorOAdmin

from .services import (
    citas_por_dia,
    demanda_por_especialidad,
    disponibilidad_proximos_dias,
    indicadores_generales,
    ocupacion_por_doctor,
    tasa_no_asistencia,
)


PARAMETROS_RANGO = [
    OpenApiParameter("desde", OpenApiTypes.DATE, description="Inicio del rango. Por defecto, 30 dias atras."),
    OpenApiParameter("hasta", OpenApiTypes.DATE, description="Fin del rango. Por defecto, hoy."),
]

esquema_reporte = extend_schema(parameters=PARAMETROS_RANGO, responses=OpenApiTypes.OBJECT)


class RangoFechasMixin:
    def rango(self, request):
        desde_texto = request.query_params.get("desde")
        hasta_texto = request.query_params.get("hasta")

        hasta = parse_date(hasta_texto) if hasta_texto else date.today()
        desde = parse_date(desde_texto) if desde_texto else hasta - timedelta(days=29)

        if desde is None or hasta is None:
            raise ValidationError({"detail": "Formato de fecha invalido. Usa YYYY-MM-DD."})
        if desde > hasta:
            raise ValidationError({"detail": "'desde' no puede ser posterior a 'hasta'."})

        return desde, hasta


@esquema_reporte
class OcupacionDoctoresView(RangoFechasMixin, APIView):
    permission_classes = [EsDoctorOAdmin]

    def get(self, request):
        desde, hasta = self.rango(request)
        return Response(
            {
                "rango": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
                "resultados": ocupacion_por_doctor(desde, hasta),
            }
        )


@esquema_reporte
class NoAsistenciaView(RangoFechasMixin, APIView):
    permission_classes = [EsDoctorOAdmin]

    def get(self, request):
        desde, hasta = self.rango(request)
        return Response(tasa_no_asistencia(desde, hasta))


@esquema_reporte
class CitasPorDiaView(RangoFechasMixin, APIView):
    permission_classes = [EsDoctorOAdmin]

    def get(self, request):
        desde, hasta = self.rango(request)
        return Response({"resultados": citas_por_dia(desde, hasta)})


@esquema_reporte
class DemandaEspecialidadView(RangoFechasMixin, APIView):
    permission_classes = [EsDoctorOAdmin]

    def get(self, request):
        desde, hasta = self.rango(request)
        return Response({"resultados": demanda_por_especialidad(desde, hasta)})


@extend_schema(
    parameters=[OpenApiParameter("dias", OpenApiTypes.INT, description="Dias a proyectar (1-30).")],
    responses=OpenApiTypes.OBJECT,
)
class DisponibilidadGlobalView(APIView):
    permission_classes = [EsDoctorOAdmin]
    throttle_scope = "disponibilidad"

    def get(self, request):
        try:
            dias = int(request.query_params.get("dias", 7))
        except ValueError:
            raise ValidationError({"dias": "Debe ser un numero entero."})
        return Response({"dias": dias, "resultados": disponibilidad_proximos_dias(min(max(dias, 1), 30))})


@esquema_reporte
class IndicadoresGeneralesView(RangoFechasMixin, APIView):
    permission_classes = [EsAdmin]

    def get(self, request):
        desde, hasta = self.rango(request)
        return Response(indicadores_generales(desde, hasta))
