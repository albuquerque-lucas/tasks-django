from django.db import models
from django.contrib.auth import get_user_model


class BaseModel(models.Model):
    """Modelo base com campos comuns"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class PriorityLevel(BaseModel):
    """Nivel de prioridade para tarefas"""
    level = models.IntegerField(
        unique=True,
        verbose_name='Nivel'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Nome'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descricao'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        verbose_name = 'Nivel de prioridade'
        verbose_name_plural = 'Niveis de prioridade'
        ordering = ('level',)

    def __str__(self):
        return f"{self.level} - {self.name}"


class Task(BaseModel):
    """Modelo de tarefa (TODO list)"""
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('in_progress', 'Em Progresso'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
    ]
    
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Usuário'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Título'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descrição'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Data de Vencimento'
    )
    priority_level = models.ForeignKey(
        PriorityLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Nivel de Prioridade'
    )
    
    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'
        ordering = ('-priority_level__level', 'due_date')
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
