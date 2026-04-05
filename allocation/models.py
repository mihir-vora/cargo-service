import uuid

from django.db import models


class OptimizationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cargos = models.JSONField()
    tanks = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    optimized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
