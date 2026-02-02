from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import PriorityLevel, Task
from .serializers import PriorityLevelSerializer, TaskSerializer
from .services.assignments import resolve_assignee, resolve_team
from .services.events import (
    log_task_create,
    log_task_delete,
    log_task_update,
    notify_task_assigned,
)
from .services.query_params import (
    apply_ordering,
    apply_search_filter,
    get_ordering,
    parse_page_params,
)
from .services.queries import get_task_queryset_for_user
from .services.roles import is_admin, is_company_admin
from .services.search import fallback_search, search_tasks_meili


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
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering_fields = [
        'id',
        'created_at',
        'updated_at',
        'title',
        'status',
        'due_date',
        'priority_level__level',
        'user__username',
        'team__name',
    ]
    ordering = ['-created_at', '-id']

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        user = request.user
        if not (is_admin(user) or is_company_admin(user)):
            return fallback_search(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                paginator=self.paginator,
                ordering=get_ordering(request, self.ordering),
                ordering_fields=self.ordering_fields,
                default_ordering=self.ordering,
                search_term=search_term,
                provider='db',
            )

        page, page_size = parse_page_params(request)
        ordering = get_ordering(request, self.ordering)

        try:
            return search_tasks_meili(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                ordering=ordering,
                ordering_fields=self.ordering_fields,
                page=page,
                page_size=page_size,
                search_term=search_term,
            )
        except Exception:
            return fallback_search(
                request=request,
                queryset=self.get_queryset(),
                serializer_getter=self.get_serializer,
                paginator=self.paginator,
                ordering=ordering,
                ordering_fields=self.ordering_fields,
                default_ordering=self.ordering,
                search_term=search_term,
                provider='db',
            )

    def get_queryset(self):
        """Retorna todas as tarefas"""
        return get_task_queryset_for_user(self.request.user)

    def perform_create(self, serializer):
        """Define usuario e status default na criacao"""
        user_id = self.request.data.get('user')
        team_id = self.request.data.get('team')
        user = resolve_assignee(self.request.user, user_id)
        team = resolve_team(self.request.user, user, team_id)

        task = serializer.save(user=user, status='created', team=team)
        log_task_create(self.request, task)
        notify_task_assigned(self.request.user, task)

    def perform_update(self, serializer):
        task = serializer.instance
        before = {
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'due_date': task.due_date,
            'user_id': task.user_id,
            'team_id': task.team_id,
            'priority_level_id': task.priority_level_id,
        }
        user_id = self.request.data.get('user')
        team_id = self.request.data.get('team')
        if user_id is not None or team_id is not None:
            user = resolve_assignee(self.request.user, user_id)
            team = resolve_team(self.request.user, user, team_id)
            task = serializer.save(user=user, team=team)
        else:
            task = serializer.save()

        after = {
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'due_date': task.due_date,
            'user_id': task.user_id,
            'team_id': task.team_id,
            'priority_level_id': task.priority_level_id,
        }
        changes = log_task_update(self.request, task, before, after)
        if 'user_id' in changes:
            notify_task_assigned(self.request.user, task)

    def perform_destroy(self, instance):
        log_task_delete(self.request, instance)
        instance.delete()

    def create(self, request, *args, **kwargs):
        """Override para adicionar tratamento de erro customizado"""
        try:
            return super().create(request, *args, **kwargs)
        except PermissionDenied as error:
            return Response({
                'message': str(error),
                'error_code': 'PERMISSION_DENIED',
                'details': None,
            }, status=status.HTTP_403_FORBIDDEN)
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
        except PermissionDenied as error:
            return Response({
                'message': str(error),
                'error_code': 'PERMISSION_DENIED',
                'details': None,
            }, status=status.HTTP_403_FORBIDDEN)
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
    def created(self, request):
        """Retorna apenas as tarefas criadas"""
        try:
            tasks = self.get_queryset().filter(status='created')
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as error:
            return Response({
                'message': 'Erro ao buscar tarefas criadas',
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

    @action(detail=False, methods=['get'])
    def mine(self, request):
        """Retorna apenas as tarefas atribuidas ao usuario autenticado."""
        if not request.user.is_authenticated:
            return Response(
                {
                    'message': 'Usuario nao autenticado',
                    'error_code': 'UNAUTHENTICATED',
                    'details': None,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        queryset = Task.objects.filter(user=request.user)
        search_term = request.query_params.get('search', '').strip()
        if search_term:
            queryset = apply_search_filter(queryset, search_term)

        ordering = get_ordering(request, self.ordering)
        queryset = apply_ordering(queryset, ordering, self.ordering_fields, self.ordering)

        page_data = self.paginator.paginate_queryset(queryset, request)
        if page_data is not None:
            serializer = self.get_serializer(page_data, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


