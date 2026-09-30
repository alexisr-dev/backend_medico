from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/auth/", include("apps.usuarios.urls")),
    path("api/pacientes/", include("apps.pacientes.urls")),
    path("api/doctores/", include("apps.doctores.urls")),
    path("api/citas/", include("apps.citas.urls")),
    path("api/historiales/", include("apps.historiales.urls")),
    path("api/notificaciones/", include("apps.notificaciones.urls")),
    path("api/reportes/", include("apps.reportes.urls")),
    path("api/auditoria/", include("apps.auditoria.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
