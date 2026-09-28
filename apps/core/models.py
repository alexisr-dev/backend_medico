import uuid

from django.db import models


class ModeloBase(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ModeloBaseUUID(ModeloBase):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta(ModeloBase.Meta):
        abstract = True
