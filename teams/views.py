from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Team
from .serializers import TeamSerializer
from tasks.serializers import TaskSerializer
from tasks.models import Task


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def _is_super_admin(self, user):
        return user.is_superuser or user.groups.filter(name='super_admin').exists()

    def _is_company_admin(self, user):
        return user.groups.filter(name='company_admin').exists()

    def _can_manage_teams(self, user):
        return self._is_super_admin(user) or self._is_company_admin(user)

    def _is_manager_for_team(self, user, team):
        return team.managers.filter(id=user.id).exists()

    def _can_edit_team(self, user, team):
        return self._can_manage_teams(user) or self._is_manager_for_team(user, team)

    def create(self, request, *args, **kwargs):
        if not self._can_manage_teams(request.user):
            raise PermissionDenied('Usuario sem permissao para criar equipes')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        team = self.get_object()
        if not self._can_edit_team(request.user, team):
            raise PermissionDenied('Usuario sem permissao para editar equipes')
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        team = self.get_object()
        if not self._can_edit_team(request.user, team):
            raise PermissionDenied('Usuario sem permissao para editar equipes')
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._can_manage_teams(request.user):
            raise PermissionDenied('Usuario sem permissao para remover equipes')
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        user = self.request.user
        if (
            not self._can_manage_teams(user)
            and 'members' in self.request.data
            and not self._is_manager_for_team(user, serializer.instance)
        ):
            raise PermissionDenied('Usuario sem permissao para alterar membros')
        serializer.save()

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        team = self.get_object()
        user = request.user
        if not (self._can_manage_teams(user) or team.members.filter(id=user.id).exists() or team.managers.filter(id=user.id).exists()):
            raise PermissionDenied('Usuario sem permissao para acessar tarefas da equipe')

        queryset = Task.objects.filter(team=team).order_by('-id')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(queryset, many=True)
        return Response(serializer.data)
