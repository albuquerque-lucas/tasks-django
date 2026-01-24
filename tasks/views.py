from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PriorityLevel, Task
from .serializers import PriorityLevelSerializer, TaskSerializer


class PriorityLevelViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar niveis de prioridade.
    """
    serializer_class = PriorityLevelSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """Retorna todos os niveis de prioridade"""
        return PriorityLevel.objects.all()


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar tarefas do usuario.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """Retorna todas as tarefas"""
        return Task.objects.all()

    def perform_create(self, serializer):
        """Define usuario e status default na criacao"""
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        user_id = self.request.data.get('user')
        if user_id:
            try:
                user = UserModel.objects.get(id=user_id)
            except UserModel.DoesNotExist:
                raise ValueError(f'Usuario com ID {user_id} nao encontrado')
        elif self.request.user.is_authenticated:
            user = self.request.user
        else:
            user = UserModel.objects.first()
            if not user:
                raise ValueError('Nenhum usuario disponivel para associar a tarefa')

        serializer.save(user=user, status='pending')

    def create(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as error:
            return Response({
                'message': str(error),
                'error_code': 'VALUE_ERROR',
                'details': None,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({
                'message': 'Erro ao criar tarefa',
                'error_code': 'CREATION_ERROR',
                'details': str(error),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as error:
            return Response({
                'message': 'Erro ao atualizar tarefa',
                'error_code': 'UPDATE_ERROR',
                'details': str(error),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as error:
            return Response({
                'message': 'Erro ao deletar tarefa',
                'error_code': 'DELETE_ERROR',
                'details': str(error),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Retorna apenas as tarefas pendentes"""
        try:
            tasks = self.get_queryset().filter(status='pending')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as error:
            return Response({
                'message': 'Erro ao buscar tarefas pendentes',
                'error_code': 'QUERY_ERROR',
                'details': str(error),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Retorna apenas as tarefas concluidas"""
        try:
            tasks = self.get_queryset().filter(status='completed')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as error:
            return Response({
                'message': 'Erro ao buscar tarefas concluidas',
                'error_code': 'QUERY_ERROR',
                'details': str(error),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
