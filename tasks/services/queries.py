from teams.models import Team
from tasks.models import Task
from .roles import is_admin, is_company_admin


def get_task_queryset_for_user(user):
    """Retorna queryset de tarefas com base na visibilidade do usuario."""
    if not user.is_authenticated:
        return Task.objects.none()

    if is_admin(user) or is_company_admin(user):
        return Task.objects.all()

    teams = (
        Team.objects.filter(members=user)
        | Team.objects.filter(managers=user)
    ).distinct()
    if not teams.exists():
        return Task.objects.none()

    return Task.objects.filter(team__in=teams)
