from django.db.models import Count
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.usuarios.permissions import EsAdmin

from .models import AuditoriaAcceso
from .serializers import AuditoriaAccesoSerializer


class AuditoriaAccesoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditoriaAccesoSerializer
    permission_classes = [EsAdmin]
    filterset_fields = ["usuario", "accion", "modelo_afectado"]
    search_fields = ["usuario__email", "objeto_id", "ruta"]
    ordering_fields = ["fecha"]

    def get_queryset(self):
        queryset = AuditoriaAcceso.objects.select_related("usuario")
        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")
        if desde:
            queryset = queryset.filter(fecha__date__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__date__lte=hasta)
        return queryset

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        base = self.get_queryset()
        return Response(
            {
                "total": base.count(),
                "por_accion": list(base.values("accion").annotate(total=Count("id")).order_by("-total")),
                "por_modelo": list(base.values("modelo_afectado").annotate(total=Count("id")).order_by("-total")),
                "top_usuarios": list(
                    base.exclude(usuario__isnull=True)
                    .values("usuario__email", "usuario__rol")
                    .annotate(total=Count("id"))
                    .order_by("-total")[:10]
                ),
            }
        )
