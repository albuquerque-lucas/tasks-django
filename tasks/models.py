from django.db import models
from django.contrib.auth import get_user_model


class BaseModel(models.Model):
    """Modelo base com campos comuns"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


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
    priority = models.IntegerField(
        default=0,
        verbose_name='Prioridade'
    )
    
    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'
        ordering = ('-priority', 'due_date')
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
