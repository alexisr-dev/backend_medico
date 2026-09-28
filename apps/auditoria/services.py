import logging

from apps.core.utils import ip_del_request

from .models import AuditoriaAcceso

logger = logging.getLogger(__name__)

BANDERA_REGISTRADO = "_auditoria_registrada"


def marcar_registrado(request) -> None:
    setattr(getattr(request, "_request", request), BANDERA_REGISTRADO, True)


def ya_registrado(request) -> bool:
    return getattr(getattr(request, "_request", request), BANDERA_REGISTRADO, False)


def registrar_acceso(request, accion: str, modelo: str, objeto_id=None) -> AuditoriaAcceso | None:
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return None

    marcar_registrado(request)

    try:
        return AuditoriaAcceso.objects.create(
            usuario=usuario,
            accion=accion,
            modelo_afectado=modelo,
            objeto_id=str(objeto_id) if objeto_id is not None else "",
            ruta=request.path[:255],
            metodo=request.method,
            ip_address=ip_del_request(request) or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
    except Exception as exc:
        logger.error("No se pudo registrar la auditoria: %s", exc)
        return None
