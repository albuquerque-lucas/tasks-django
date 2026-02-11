from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from django.apps import apps
from users.services.roles import is_company_admin, is_super_admin


def _presence_ttl_seconds():
    return getattr(settings, 'PRESENCE_TTL_SECONDS', 75)


def _last_seen_min_update_seconds():
    return getattr(settings, 'PRESENCE_LAST_SEEN_UPDATE_SECONDS', 60)


def _presence_key(user_id):
    return f'presence:user:{user_id}'


def _last_seen_rate_key(user_id):
    return f'presence:last_seen:{user_id}'


def mark_user_online(user_id, now=None):
    ttl = _presence_ttl_seconds()
    cache.set(_presence_key(user_id), (now or timezone.now()).isoformat(), timeout=ttl)


def mark_user_offline(user_id):
    cache.delete(_presence_key(user_id))


def is_user_online(user_id):
    return cache.get(_presence_key(user_id)) is not None


def get_online_map(user_ids):
    if not user_ids:
        return {}
    key_map = {_presence_key(user_id): user_id for user_id in user_ids}
    cached = cache.get_many(key_map.keys())
    return {key_map[key]: True for key in cached.keys()}


def touch_last_seen(user, now=None, force=False):
    if not user or not user.is_authenticated:
        return False
    now = now or timezone.now()
    rate_key = _last_seen_rate_key(user.id)
    if force:
        cache.set(rate_key, now.isoformat(), timeout=_last_seen_min_update_seconds())
    else:
        added = cache.add(rate_key, now.isoformat(), timeout=_last_seen_min_update_seconds())
        if not added:
            return False
    user.last_seen_at = now
    user.save(update_fields=['last_seen_at'])
    return True


def get_presence_queryset(viewer, team=None):
    User = get_user_model()
    if not viewer.is_authenticated:
        return User.objects.none()

    if is_super_admin(viewer) or is_company_admin(viewer):
        if team is not None:
            return User.objects.filter(Q(teams=team) | Q(managed_teams=team)).distinct()
        return User.objects.all()

    if team is not None:
        return User.objects.filter(
            Q(teams=team) | Q(managed_teams=team) | Q(id=viewer.id)
        ).distinct()

    Team = apps.get_model('teams', 'Team')
    teams = Team.objects.filter(Q(members=viewer) | Q(managers=viewer)).distinct()
    if not teams.exists():
        return User.objects.filter(id=viewer.id)
    return User.objects.filter(
        Q(teams__in=teams) | Q(managed_teams__in=teams) | Q(id=viewer.id)
    ).distinct()


def get_presence_recipient_ids(target_user):
    User = get_user_model()
    if not target_user or not target_user.is_authenticated:
        return []

    if is_super_admin(target_user) or is_company_admin(target_user):
        return list(User.objects.values_list('id', flat=True))

    Team = apps.get_model('teams', 'Team')
    teams = Team.objects.filter(Q(members=target_user) | Q(managers=target_user)).distinct()
    if not teams.exists():
        return [target_user.id]

    recipients = User.objects.filter(
        Q(teams__in=teams)
        | Q(managed_teams__in=teams)
        | Q(is_superuser=True)
        | Q(groups__name__in=['super_admin', 'company_admin'])
    ).distinct()
    return list(recipients.values_list('id', flat=True))
