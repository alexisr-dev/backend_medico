from functools import lru_cache

from django.conf import settings
from django.db import models

from cryptography.fernet import Fernet, InvalidToken

PREFIJO_CIFRADO = "enc::"


@lru_cache(maxsize=1)
def _motor() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode())


def cifrar(texto):
    if not texto:
        return texto
    return PREFIJO_CIFRADO + _motor().encrypt(texto.encode()).decode()


def descifrar(texto):
    if not texto or not texto.startswith(PREFIJO_CIFRADO):
        return texto
    try:
        return _motor().decrypt(texto[len(PREFIJO_CIFRADO):].encode()).decode()
    except InvalidToken:
        return ""


class TextoCifradoField(models.TextField):
    description = "Texto cifrado a nivel de aplicacion con Fernet (AES-128-CBC + HMAC)"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return cifrar(value)

    def from_db_value(self, value, expression, connection):
        return descifrar(value)

    def to_python(self, value):
        if isinstance(value, str) and value.startswith(PREFIJO_CIFRADO):
            return descifrar(value)
        return value


class CharCifradoField(models.CharField):
    description = "Cadena corta cifrada a nivel de aplicacion con Fernet"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 512)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return cifrar(value)

    def from_db_value(self, value, expression, connection):
        return descifrar(value)

    def to_python(self, value):
        if isinstance(value, str) and value.startswith(PREFIJO_CIFRADO):
            return descifrar(value)
        return value


class CIEmailField(models.EmailField):
    description = "Email case-insensitive respaldado por la extension citext de PostgreSQL"

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return "citext"
        return super().db_type(connection)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value.strip().lower() if isinstance(value, str) else value
