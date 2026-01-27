from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import PriorityLevel, Task
from .serializers import PriorityLevelSerializer, TaskSerializer
from django.contrib.auth import get_user_model
from teams.models import Team


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

    def get_queryset(self):
        """Retorna todas as tarefas"""
        user = self.request.user
        if not user.is_authenticated:
            return Task.objects.none()

        if self._is_admin(user) or self._is_company_admin(user):
            return Task.objects.all().order_by('-id')

        teams = (
            Team.objects.filter(members=user)
            | Team.objects.filter(managers=user)
        ).distinct()
        if not teams.exists():
            return Task.objects.none()

        return Task.objects.filter(team__in=teams).order_by('-id')

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

        serializer.save(user=user, status='pending', team=team)

    def perform_update(self, serializer):
        user_id = self.request.data.get('user')
        team_id = self.request.data.get('team')
        if user_id is not None or team_id is not None:
            user = self._resolve_assignee(user_id)
            team = self._resolve_team(user, team_id)
            serializer.save(user=user, team=team)
        else:
            serializer.save()

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
