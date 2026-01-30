import math
from django.db.models import Case, IntegerField, Q, When
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
from safetodo.services.meili import search_teams


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering_fields = ['id', 'name', 'created_at']
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
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                direction = 'desc' if item.startswith('-') else 'asc'
                return [f'{field}:{direction}']
        return ['id:desc']

    def _build_page_link(self, request, page):
        params = request.query_params.copy()
        params['page'] = page
        return request.build_absolute_uri(f'?{params.urlencode()}')

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        page, page_size = self._parse_page_params(request)
        ordering = self._get_ordering(request)
        meili_sort = self._get_meili_sort(ordering)
        offset = (page - 1) * page_size

        is_numeric = search_term.isdigit()
        filter_value = f'id = {int(search_term)}' if is_numeric else None
        query = '' if is_numeric else search_term

        try:
            meili_result = search_teams(
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
                results = self.get_queryset().filter(id__in=ids).order_by(preserved)

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
        search_filter = Q(name__icontains=search_term) | Q(description__icontains=search_term)
        if search_term.isdigit():
            search_filter |= Q(id=int(search_term))
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

        queryset = Task.objects.filter(team=team)
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering:
            queryset = queryset.order_by(ordering)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskSerializer(queryset, many=True)
        return Response(serializer.data)
