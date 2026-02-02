from django.db.models import Q
from teams.models import Team


def is_super_admin(user):
    return user.is_superuser or user.groups.filter(name='super_admin').exists()


def is_company_admin(user):
    return user.groups.filter(name='company_admin').exists()


def can_manage_teams(user):
    return is_super_admin(user) or is_company_admin(user)


def is_manager_for_team(user, team):
    return team.managers.filter(id=user.id).exists()


def can_edit_team(user, team):
    return can_manage_teams(user) or is_manager_for_team(user, team)


def allowed_teams(user):
    if not user.is_authenticated:
        return Team.objects.none()
    if can_manage_teams(user):
        return Team.objects.all()
    return Team.objects.filter(Q(members=user) | Q(managers=user)).distinct()
