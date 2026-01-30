import math
from django.db.models import Case, IntegerField, Q, When
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import PriorityLevel, Task
from .serializers import PriorityLevelSerializer, TaskSerializer
from django.contrib.auth import get_user_model
from teams.models import Team
from auditlogs.utils import log_audit_event
from notifications.utils import notify
from safetodo.services.meili import search_tasks


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

    def _parse_page_params(self, request):
        try:
            page = int(request.query_params.get('page', 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 10))
        except ValueError:
            page_size = 10
        page = max(1, page)
        page_size = max(1, min(page_size, 500))
        return page, page_size

    def _get_ordering(self, request):
        ordering_param = request.query_params.get('ordering')
        if ordering_param:
            return [item.strip() for item in ordering_param.split(',') if item.strip()]
        return list(self.ordering or [])

    def _get_meili_sort(self, ordering):
        if not ordering:
            return ['id:desc']
        ordering_fields = set(self.ordering_fields or [])
        mapping = {
            'priority_level__level': 'priority_level',
            'user__username': 'user_username',
            'team__name': 'team_name',
        }
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                meili_field = mapping.get(field, field)
                direction = 'desc' if item.startswith('-') else 'asc'
                return [f'{meili_field}:{direction}']
        return ['id:desc']

    def _build_page_link(self, request, page):
        params = request.query_params.copy()
        params['page'] = page
        return request.build_absolute_uri(f'?{params.urlencode()}')

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        user = request.user
        if not (self._is_admin(user) or self._is_company_admin(user)):
            return self._fallback_search(request, search_term)

        page, page_size = self._parse_page_params(request)
        ordering = self._get_ordering(request)
        meili_sort = self._get_meili_sort(ordering)
        offset = (page - 1) * page_size

        is_numeric = search_term.isdigit()
        filter_value = f'id = {int(search_term)}' if is_numeric else None
        query = '' if is_numeric else search_term

        try:
            meili_result = search_tasks(
                query=query,
                offset=offset,
                limit=page_size,
                sort=meili_sort,
                filter_value=filter_value,
            )
            hits = meili_result.get('hits', [])
            total = meili_result.get('estimatedTotalHits') or meili_result.get('nbHits') or 0
            ids = [item.get('id') for item in hits if item.get('id') is not None]
            if not ids:
                results = []
            else:
                preserved = Case(
                    *[When(id=pk, then=pos) for pos, pk in enumerate(ids)],
                    output_field=IntegerField(),
                )
                results = (
                    self.get_queryset()
                    .filter(id__in=ids)
                    .order_by(preserved)
                )

            serializer = self.get_serializer(results, many=True)
            total_pages = math.ceil(total / page_size) if page_size else 1
            next_link = self._build_page_link(request, page + 1) if page < total_pages else None
            prev_link = self._build_page_link(request, page - 1) if page > 1 else None
            response = Response(
                {
                    'count': total,
                    'next': next_link,
                    'previous': prev_link,
                    'results': serializer.data,
                }
            )
            response['X-Search-Provider'] = 'meili'
            return response
        except Exception:
            return self._fallback_search(request, search_term, provider='db')

    def _fallback_search(self, request, search_term, provider='db'):
        queryset = self.get_queryset()
        search_filter = (
            Q(title__icontains=search_term)
            | Q(description__icontains=search_term)
            | Q(status__icontains=search_term)
            | Q(priority_level__name__icontains=search_term)
            | Q(user__username__icontains=search_term)
            | Q(user__email__icontains=search_term)
            | Q(user__first_name__icontains=search_term)
            | Q(user__last_name__icontains=search_term)
            | Q(team__name__icontains=search_term)
        )
        if search_term.isdigit():
            search_filter |= Q(id=int(search_term))
            search_filter |= Q(priority_level__level=int(search_term))
        queryset = queryset.filter(search_filter)

        ordering = self._get_ordering(request)
        valid_ordering = []
        ordering_fields = set(self.ordering_fields or [])
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                valid_ordering.append(item)
        if valid_ordering:
            queryset = queryset.order_by(*valid_ordering)
        elif self.ordering:
            queryset = queryset.order_by(*self.ordering)

        paginator = self.paginator
        page_data = paginator.paginate_queryset(queryset, request)
        response = paginator.get_paginated_response(
            self.get_serializer(page_data, many=True).data
        )
        response['X-Search-Provider'] = provider
        return response

    def get_queryset(self):
        """Retorna todas as tarefas"""
        user = self.request.user
        if not user.is_authenticated:
            return Task.objects.none()

        if self._is_admin(user) or self._is_company_admin(user):
            return Task.objects.all()

        teams = (
            Team.objects.filter(members=user)
            | Team.objects.filter(managers=user)
        ).distinct()
        if not teams.exists():
            return Task.objects.none()

        return Task.objects.filter(team__in=teams)

    def _is_admin(self, user):
        return user.is_superuser or user.groups.filter(name='super_admin').exists()

    def _is_company_admin(self, user):
        return user.groups.filter(name='company_admin').exists()

    def _allowed_teams_for_assignment(self, user):
        if self._is_admin(user) or self._is_company_admin(user):
            return Team.objects.all()
        if Team.objects.filter(managers=user).exists():
            return Team.objects.filter(managers=user)
        return Team.objects.filter(members=user)

    def _resolve_assignee(self, user_id):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied('Usuario nao autenticado')

        if self._is_admin(user) or self._is_company_admin(user):
            if user_id:
                UserModel = get_user_model()
                try:
                    return UserModel.objects.get(id=user_id)
                except UserModel.DoesNotExist:
                    raise ValueError(f'Usuario com ID {user_id} nao encontrado')
            return user

        if Team.objects.filter(managers=user).exists():
            if not user_id:
                return user
            UserModel = get_user_model()
            try:
                assignee = UserModel.objects.get(id=user_id)
            except UserModel.DoesNotExist:
                raise ValueError(f'Usuario com ID {user_id} nao encontrado')
            allowed_teams = self._allowed_teams_for_assignment(user)
            if not Team.objects.filter(id__in=allowed_teams, members=assignee).exists():
                raise PermissionDenied('Usuario fora das equipes permitidas')
            return assignee

        if user_id and str(user_id) != str(user.id):
            raise PermissionDenied('Usuario nao pode atribuir tarefa para outro usuario')

        return user

    def _resolve_team(self, assignee, team_id):
        allowed_teams = self._allowed_teams_for_assignment(self.request.user)
        if team_id:
            team = Team.objects.filter(id=team_id).first()
            if not team:
                raise ValueError('Equipe nao encontrada')
            if not allowed_teams.filter(id=team.id).exists():
                raise PermissionDenied('Equipe fora das equipes permitidas')
            if not team.members.filter(id=assignee.id).exists():
                raise PermissionDenied('Usuario nao pertence a equipe informada')
            return team

        teams = Team.objects.filter(members=assignee, id__in=allowed_teams)
        if teams.count() == 1:
            return teams.first()
        if teams.count() == 0:
            raise PermissionDenied('Usuario nao pertence a nenhuma equipe')
        raise PermissionDenied('Equipe obrigatoria para usuarios em multiplas equipes')

    def perform_create(self, serializer):
        """Define usuario e status default na criacao"""
        user_id = self.request.data.get('user')
        team_id = self.request.data.get('team')
        user = self._resolve_assignee(user_id)
        team = self._resolve_team(user, team_id)

        task = serializer.save(user=user, status='created', team=team)
        log_audit_event(
            self.request,
            action='task.create',
            entity_type='Task',
            entity_id=task.id,
            metadata={
                'title': task.title,
                'user_id': task.user_id,
                'team_id': task.team_id,
                'priority_level_id': task.priority_level_id,
                'status': task.status,
            },
        )
        notify(
            recipient=user,
            type='task.assigned',
            payload={
                'task_id': task.id,
                'team_id': task.team_id,
                'actor_id': self.request.user.id,
            },
            actor=self.request.user,
        )

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
            user = self._resolve_assignee(user_id)
            team = self._resolve_team(user, team_id)
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
        changes = {
            key: {'from': before[key], 'to': after[key]}
            for key in before
            if before[key] != after[key]
        }
        if changes:
            log_audit_event(
                self.request,
                action='task.update',
                entity_type='Task',
                entity_id=task.id,
                metadata={'changes': changes},
            )
        if 'user_id' in changes:
            notify(
                recipient=task.user,
                type='task.assigned',
                payload={
                    'task_id': task.id,
                    'team_id': task.team_id,
                    'actor_id': self.request.user.id,
                },
                actor=self.request.user,
            )

    def perform_destroy(self, instance):
        log_audit_event(
            self.request,
            action='task.delete',
            entity_type='Task',
            entity_id=instance.id,
            metadata={
                'title': instance.title,
                'user_id': instance.user_id,
                'team_id': instance.team_id,
                'priority_level_id': instance.priority_level_id,
                'status': instance.status,
            },
        )
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


