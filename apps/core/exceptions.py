import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ErrorNegocio(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "La operacion no pudo completarse."
    default_code = "error_negocio"


class HorarioNoDisponible(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El horario seleccionado ya no esta disponible."
    default_code = "horario_no_disponible"


class ConflictoDeVersion(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La cita fue modificada por otro usuario. Recarga e intenta de nuevo."
    default_code = "conflicto_version"


def manejador_excepciones(exc, context):
    if isinstance(exc, DjangoValidationError):
        return Response(
            {"detail": "Datos invalidos.", "codigo": "validacion", "errores": exc.message_dict if hasattr(exc, "message_dict") else exc.messages},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError capturado en API: %s", exc)
        return Response(
            {"detail": "El horario seleccionado ya no esta disponible.", "codigo": "horario_no_disponible"},
            status=status.HTTP_409_CONFLICT,
        )

    respuesta = exception_handler(exc, context)

    if respuesta is None:
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(
            {"detail": "Error interno del servidor.", "codigo": "error_interno"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    codigo = getattr(exc, "default_code", "error")
    if isinstance(exc, Http404):
        codigo = "no_encontrado"
    elif isinstance(exc, PermissionDenied):
        codigo = "permiso_denegado"

    if isinstance(respuesta.data, dict) and "detail" in respuesta.data:
        respuesta.data["codigo"] = codigo
    elif isinstance(respuesta.data, dict):
        respuesta.data = {"detail": "Datos invalidos.", "codigo": "validacion", "errores": respuesta.data}
    elif isinstance(respuesta.data, list):
        respuesta.data = {"detail": "Datos invalidos.", "codigo": "validacion", "errores": respuesta.data}

    return respuesta
