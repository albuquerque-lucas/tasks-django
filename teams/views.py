from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Team
from .serializers import TeamSerializer
from tasks.models import Task
from tasks.serializers import TaskSerializer
from users.serializers import UserSerializer
from .services.events import (
    log_managers_changed,
    log_members_changed,
    log_team_create,
    log_team_delete,
    log_team_update,
)
from .services.query_params import (
    apply_ordering,
    get_ordering,
    parse_page_params,
)
from .services.roles import (
    allowed_teams,
    can_edit_team,
    can_manage_teams,
    is_manager_for_team,
)
from .services.search import fallback_search, search_teams_meili
from .services.task_filters import apply_team_task_search_filter


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering_fields = ['id', 'name', 'created_at']
    ordering = ['-created_at', '-id']
    member_ordering_fields = [
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'date_joined',
    ]
    task_ordering_fields = [
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

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        page, page_size = parse_page_params(request)
        ordering = get_ordering(request, self.ordering)

        try:
            return search_teams_meili(
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
        return allowed_teams(self.request.user)

    def create(self, request, *args, **kwargs):
        if not can_manage_teams(request.user):
            raise PermissionDenied('Usuario sem permissao para criar equipes')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        team = self.get_object()
        if not can_edit_team(request.user, team):
            raise PermissionDenied('Usuario sem permissao para editar equipes')
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        team = self.get_object()
        if not can_edit_team(request.user, team):
            raise PermissionDenied('Usuario sem permissao para editar equipes')
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not can_manage_teams(request.user):
            raise PermissionDenied('Usuario sem permissao para remover equipes')
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        team = serializer.save()
        log_team_create(self.request, team)

    def perform_update(self, serializer):
        team = serializer.instance
        before_members = set(team.members.values_list('id', flat=True))
        before_managers = set(team.managers.values_list('id', flat=True))
        before = {
            'name': team.name,
            'description': team.description,
        }

        user = self.request.user
        if (
            not can_manage_teams(user)
            and 'members' in self.request.data
            and not is_manager_for_team(user, team)
        ):
            raise PermissionDenied('Usuario sem permissao para alterar membros')

        team = serializer.save()

        after_members = set(team.members.values_list('id', flat=True))
        after_managers = set(team.managers.values_list('id', flat=True))
        after = {
            'name': team.name,
            'description': team.description,
        }

        log_team_update(self.request, team, before, after)

        added_members = sorted(after_members - before_members)
        removed_members = sorted(before_members - after_members)
        log_members_changed(self.request, team, added_members, removed_members)

        added_managers = sorted(after_managers - before_managers)
        removed_managers = sorted(before_managers - after_managers)
        log_managers_changed(self.request, team, added_managers, removed_managers)

    def perform_destroy(self, instance):
        log_team_delete(self.request, instance)
        instance.delete()

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        team = self.get_object()
        user = request.user
        if not (can_manage_teams(user) or team.members.filter(id=user.id).exists() or team.managers.filter(id=user.id).exists()):
            raise PermissionDenied('Usuario sem permissao para acessar tarefas da equipe')

        queryset = Task.objects.filter(team=team)
        search_term = request.query_params.get('search', '').strip()
        if search_term:
            queryset = apply_team_task_search_filter(queryset, search_term)

        ordering = get_ordering(request, self.ordering)
        queryset = apply_ordering(
            queryset,
            ordering,
            self.task_ordering_fields,
            default_ordering=['-created_at', '-id'],
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        team = self.get_object()
        user = request.user
        if not (can_manage_teams(user) or team.members.filter(id=user.id).exists() or team.managers.filter(id=user.id).exists()):
            raise PermissionDenied('Usuario sem permissao para acessar membros da equipe')

        queryset = team.members.all().distinct()
        ordering_list = get_ordering(request, ['-date_joined', '-id'])
        queryset = apply_ordering(
            queryset,
            ordering_list,
            self.member_ordering_fields,
            default_ordering=['-date_joined', '-id'],
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)
