from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    CambiarPasswordView,
    LoginView,
    PerfilActualView,
    RegistroDoctorView,
    RegistroPacienteView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("registro/", RegistroPacienteView.as_view(), name="registro_paciente"),
    path("registro-doctor/", RegistroDoctorView.as_view(), name="registro_doctor"),
    path("yo/", PerfilActualView.as_view(), name="perfil_actual"),
    path("cambiar-password/", CambiarPasswordView.as_view(), name="cambiar_password"),
    path("", include(router.urls)),
]
