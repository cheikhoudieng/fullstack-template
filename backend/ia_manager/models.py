import uuid
from django.db import models
from user_auth.models import User

class IAInteraction(models.Model): 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    model_name = models.CharField(max_length=100)
    input_data = models.JSONField(null=True, blank=True)
    output_data = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Interaction IA"
        verbose_name_plural = "Interactions IA"
        ordering = ['-created_at']  # Pour trier par date de création décroissante

    def __str__(self):
        return f"Interaction IA - {self.created_at.strftime('%Y-%m-%d %H:%M')}"