from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Team
from .serializers import TeamSerializer
from tasks.serializers import TaskSerializer
from tasks.models import Task
from auditlogs.utils import log_audit_event
from notifications.utils import notify


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

    def perform_create(self, serializer):
        team = serializer.save()
        log_audit_event(
            self.request,
            action='team.create',
            entity_type='Team',
            entity_id=team.id,
            metadata={
                'name': team.name,
                'description': team.description,
            },
        )

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
            not self._can_manage_teams(user)
            and 'members' in self.request.data
            and not self._is_manager_for_team(user, team)
        ):
            raise PermissionDenied('Usuario sem permissao para alterar membros')

        team = serializer.save()

        after_members = set(team.members.values_list('id', flat=True))
        after_managers = set(team.managers.values_list('id', flat=True))
        after = {
            'name': team.name,
            'description': team.description,
        }

        changes = {
            key: {'from': before[key], 'to': after[key]}
            for key in before
            if before[key] != after[key]
        }
        if changes:
            log_audit_event(
                self.request,
                action='team.update',
                entity_type='Team',
                entity_id=team.id,
                metadata={'changes': changes},
            )

        added_members = sorted(after_members - before_members)
        removed_members = sorted(before_members - after_members)
        if added_members:
            log_audit_event(
                self.request,
                action='team.members.add',
                entity_type='Team',
                entity_id=team.id,
                metadata={'member_ids': added_members},
            )
            recipients = {
                member.id: member
                for member in team.members.filter(id__in=added_members)
            }
            for member_id in added_members:
                recipient = recipients.get(member_id)
                if not recipient:
                    continue
                notify(
                    recipient=recipient,
                    type='team.member_added',
                    payload={
                        'team_id': team.id,
                        'actor_id': self.request.user.id,
                    },
                    actor=self.request.user,
                )
        if removed_members:
            log_audit_event(
                self.request,
                action='team.members.remove',
                entity_type='Team',
                entity_id=team.id,
                metadata={'member_ids': removed_members},
            )

        added_managers = sorted(after_managers - before_managers)
        removed_managers = sorted(before_managers - after_managers)
        if added_managers:
            log_audit_event(
                self.request,
                action='team.managers.add',
                entity_type='Team',
                entity_id=team.id,
                metadata={'manager_ids': added_managers},
            )
        if removed_managers:
            log_audit_event(
                self.request,
                action='team.managers.remove',
                entity_type='Team',
                entity_id=team.id,
                metadata={'manager_ids': removed_managers},
            )

    def perform_destroy(self, instance):
        log_audit_event(
            self.request,
            action='team.delete',
            entity_type='Team',
            entity_id=instance.id,
            metadata={
                'name': instance.name,
                'description': instance.description,
            },
        )
        instance.delete()

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
