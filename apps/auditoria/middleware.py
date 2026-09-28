from .models import AccionAuditoria
from .services import registrar_acceso, ya_registrado

RUTAS_SENSIBLES = {
    "/api/historiales/": "HistorialMedico",
    "/api/historiales/consultas/": "RegistroConsulta",
    "/api/historiales/recetas/": "Receta",
    "/api/historiales/archivos/": "ArchivoMedico",
}

ACCION_POR_METODO = {
    "GET": AccionAuditoria.LECTURA,
    "HEAD": AccionAuditoria.LECTURA,
    "POST": AccionAuditoria.ESCRITURA,
    "PUT": AccionAuditoria.ESCRITURA,
    "PATCH": AccionAuditoria.ESCRITURA,
    "DELETE": AccionAuditoria.ELIMINACION,
}


class AuditoriaAccesoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)

        modelo = self._modelo_para(request.path)
        if modelo and 200 <= respuesta.status_code < 300:
            accion = ACCION_POR_METODO.get(request.method)
            if accion and not ya_registrado(request):
                registrar_acceso(request, accion, modelo)

        return respuesta

    def _modelo_para(self, ruta: str):
        coincidencias = [(prefijo, modelo) for prefijo, modelo in RUTAS_SENSIBLES.items() if ruta.startswith(prefijo)]
        if not coincidencias:
            return None
        return max(coincidencias, key=lambda par: len(par[0]))[1]
