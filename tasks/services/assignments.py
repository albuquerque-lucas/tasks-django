from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from teams.models import Team
from .roles import is_admin, is_company_admin


def allowed_teams_for_assignment(user):
    if is_admin(user) or is_company_admin(user):
        return Team.objects.all()
    if Team.objects.filter(managers=user).exists():
        return Team.objects.filter(managers=user)
    return Team.objects.filter(members=user)


def resolve_assignee(request_user, user_id):
    if not request_user.is_authenticated:
        raise PermissionDenied('Usuario nao autenticado')

    if is_admin(request_user) or is_company_admin(request_user):
        if user_id:
            user_model = get_user_model()
            try:
                return user_model.objects.get(id=user_id)
            except user_model.DoesNotExist:
                raise ValueError(f'Usuario com ID {user_id} nao encontrado')
        return request_user

    if Team.objects.filter(managers=request_user).exists():
        if not user_id:
            return request_user
        user_model = get_user_model()
        try:
            assignee = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            raise ValueError(f'Usuario com ID {user_id} nao encontrado')
        allowed_teams = allowed_teams_for_assignment(request_user)
        if not Team.objects.filter(id__in=allowed_teams, members=assignee).exists():
            raise PermissionDenied('Usuario fora das equipes permitidas')
        return assignee

    if user_id and str(user_id) != str(request_user.id):
        raise PermissionDenied('Usuario nao pode atribuir tarefa para outro usuario')

    return request_user


def resolve_team(request_user, assignee, team_id):
    allowed_teams = allowed_teams_for_assignment(request_user)
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
