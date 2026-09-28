from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.permissions import EsAdmin

from .models import Notificacion, Recordatorio
from .serializers import NotificacionSerializer, RecordatorioSerializer
from .services import procesar_recordatorios_pendientes


class NotificacionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = NotificacionSerializer
    queryset = Notificacion.objects.none()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["leido", "tipo"]

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)

    @action(detail=True, methods=["post"], url_path="marcar-leida")
    def marcar_leida(self, request, pk=None):
        notificacion = self.get_object()
        notificacion.leido = True
        notificacion.save(update_fields=["leido", "updated_at"])
        return Response(NotificacionSerializer(notificacion).data)

    @action(detail=False, methods=["post"], url_path="marcar-todas")
    def marcar_todas(self, request):
        actualizadas = self.get_queryset().filter(leido=False).update(leido=True)
        return Response({"actualizadas": actualizadas})

    @action(detail=False, methods=["get"], url_path="no-leidas")
    def no_leidas(self, request):
        return Response({"total": self.get_queryset().filter(leido=False).count()})


class RecordatorioViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = RecordatorioSerializer
    permission_classes = [EsAdmin]
    filterset_fields = ["enviado", "tipo", "cita"]

    def get_queryset(self):
        return Recordatorio.objects.select_related("cita")

    @action(detail=False, methods=["post"])
    def procesar(self, request):
        return Response(procesar_recordatorios_pendientes())
