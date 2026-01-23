from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar tarefas do usuário.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_queryset(self):
        """Retorna todas as tarefas"""
        return Task.objects.all()
    
    def perform_create(self, serializer):
        """Define o usuário da tarefa como o primeiro usuário ou o autenticado"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Se há user_id na requisição, usa ele, senão usa o primeiro usuário
        user_id = self.request.data.get('user')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValueError(f'Usuário com ID {user_id} não encontrado')
        elif self.request.user.is_authenticated:
            user = self.request.user
        else:
            user = User.objects.first()
            if not user:
                raise ValueError('Nenhum usuário disponível para associar a tarefa')
        
        serializer.save(user=user)
    
    def create(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as e:
            return Response({
                'message': str(e),
                'error_code': 'VALUE_ERROR',
                'details': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'message': 'Erro ao criar tarefa',
                'error_code': 'CREATION_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return Response({
                'message': 'Erro ao atualizar tarefa',
                'error_code': 'UPDATE_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({
                'message': 'Erro ao deletar tarefa',
                'error_code': 'DELETE_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Retorna apenas as tarefas pendentes"""
        try:
            tasks = self.get_queryset().filter(status='pending')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({
                'message': 'Erro ao buscar tarefas pendentes',
                'error_code': 'QUERY_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Retorna apenas as tarefas concluídas"""
        try:
            tasks = self.get_queryset().filter(status='completed')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({
                'message': 'Erro ao buscar tarefas concluídas',
                'error_code': 'QUERY_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

