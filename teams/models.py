from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Shared timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Team(BaseModel):
    """Team of users."""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teams',
        blank=True,
    )
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='managed_teams',
        blank=True,
    )

    class Meta:
        verbose_name = 'Equipe'
        verbose_name_plural = 'Equipes'

    def __str__(self):
        return self.name
