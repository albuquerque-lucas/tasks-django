import logging

from django.conf import settings
import meilisearch

logger = logging.getLogger(__name__)


class MeiliClient:
    def __init__(self):
        self.host = settings.MEILI_HOST
        self.api_key = settings.MEILI_API_KEY

    @property
    def enabled(self):
        return bool(self.host)

    def get_client(self):
        if not self.enabled:
            return None
        return meilisearch.Client(self.host, self.api_key or None)

    def health(self):
        client = self.get_client()
        if not client:
            return False
        try:
            client.health()
            return True
        except Exception:
            return False


def get_users_index(client=None):
    if client is None:
        client = MeiliClient().get_client()
    if client is None:
        return None
    return client.index(settings.MEILI_USERS_INDEX)


def ensure_users_index(index):
    if index is None:
        return None
    settings_payload = {
        'searchableAttributes': [
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
        ],
        'filterableAttributes': ['id'],
        'sortableAttributes': [
            'id',
            'date_joined',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
        ],
    }
    index.update_settings(settings_payload)
    return index


def build_user_document(user):
    first_name = user.first_name or ''
    last_name = user.last_name or ''
    full_name = f'{first_name} {last_name}'.strip()
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'full_name': full_name,
        'phone': user.phone or '',
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }


def search_users(query, offset, limit, sort=None, filter_value=None):
    index = get_users_index()
    if index is None:
        raise RuntimeError('Meilisearch client not configured')
    ensure_users_index(index)
    payload = {
        'offset': offset,
        'limit': limit,
    }
    if sort:
        payload['sort'] = sort
    if filter_value:
        payload['filter'] = filter_value
    return index.search(query, payload)


def upsert_user(user):
    try:
        index = get_users_index()
        if index is None:
            return
        ensure_users_index(index)
        index.add_documents([build_user_document(user)], primary_key='id')
    except Exception as exc:
        logger.warning('Falha ao indexar usuario no Meili: %s', exc)


def delete_user(user_id):
    try:
        index = get_users_index()
        if index is None:
            return
        index.delete_document(user_id)
    except Exception as exc:
        logger.warning('Falha ao remover usuario do Meili: %s', exc)


def get_tasks_index(client=None):
    if client is None:
        client = MeiliClient().get_client()
    if client is None:
        return None
    return client.index(settings.MEILI_TASKS_INDEX)


def ensure_tasks_index(index):
    if index is None:
        return None
    settings_payload = {
        'searchableAttributes': [
            'title',
            'description',
            'status',
            'priority_name',
            'priority_level',
            'user_username',
            'user_email',
            'user_full_name',
            'team_name',
        ],
        'filterableAttributes': ['id', 'status', 'priority_level', 'user_id', 'team_id'],
        'sortableAttributes': [
            'id',
            'created_at',
            'updated_at',
            'title',
            'status',
            'due_date',
            'priority_level',
            'user_username',
            'team_name',
        ],
    }
    index.update_settings(settings_payload)
    return index


def build_task_document(task):
    user = getattr(task, 'user', None)
    team = getattr(task, 'team', None)
    priority = getattr(task, 'priority_level', None)
    full_name = ''
    if user:
        first_name = getattr(user, 'first_name', '') or ''
        last_name = getattr(user, 'last_name', '') or ''
        full_name = f'{first_name} {last_name}'.strip()
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description or '',
        'status': task.status,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'priority_level': priority.level if priority else None,
        'priority_name': priority.name if priority else '',
        'user_id': user.id if user else None,
        'user_username': user.username if user else '',
        'user_email': user.email if user else '',
        'user_full_name': full_name,
        'team_id': team.id if team else None,
        'team_name': team.name if team else '',
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    }


def search_tasks(query, offset, limit, sort=None, filter_value=None):
    index = get_tasks_index()
    if index is None:
        raise RuntimeError('Meilisearch client not configured')
    ensure_tasks_index(index)
    payload = {'offset': offset, 'limit': limit}
    if sort:
        payload['sort'] = sort
    if filter_value:
        payload['filter'] = filter_value
    return index.search(query, payload)


def upsert_task(task):
    try:
        index = get_tasks_index()
        if index is None:
            return
        ensure_tasks_index(index)
        index.add_documents([build_task_document(task)], primary_key='id')
    except Exception as exc:
        logger.warning('Falha ao indexar tarefa no Meili: %s', exc)


def delete_task(task_id):
    try:
        index = get_tasks_index()
        if index is None:
            return
        index.delete_document(task_id)
    except Exception as exc:
        logger.warning('Falha ao remover tarefa do Meili: %s', exc)


def get_teams_index(client=None):
    if client is None:
        client = MeiliClient().get_client()
    if client is None:
        return None
    return client.index(settings.MEILI_TEAMS_INDEX)


def ensure_teams_index(index):
    if index is None:
        return None
    settings_payload = {
        'searchableAttributes': ['name', 'description'],
        'filterableAttributes': ['id'],
        'sortableAttributes': ['id', 'name', 'created_at'],
    }
    index.update_settings(settings_payload)
    return index


def build_team_document(team):
    return {
        'id': team.id,
        'name': team.name,
        'description': team.description or '',
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None,
    }


def search_teams(query, offset, limit, sort=None, filter_value=None):
    index = get_teams_index()
    if index is None:
        raise RuntimeError('Meilisearch client not configured')
    ensure_teams_index(index)
    payload = {'offset': offset, 'limit': limit}
    if sort:
        payload['sort'] = sort
    if filter_value:
        payload['filter'] = filter_value
    return index.search(query, payload)


def upsert_team(team):
    try:
        index = get_teams_index()
        if index is None:
            return
        ensure_teams_index(index)
        index.add_documents([build_team_document(team)], primary_key='id')
    except Exception as exc:
        logger.warning('Falha ao indexar equipe no Meili: %s', exc)


def delete_team(team_id):
    try:
        index = get_teams_index()
        if index is None:
            return
        index.delete_document(team_id)
    except Exception as exc:
        logger.warning('Falha ao remover equipe do Meili: %s', exc)


def get_auditlogs_index(client=None):
    if client is None:
        client = MeiliClient().get_client()
    if client is None:
        return None
    return client.index(settings.MEILI_AUDITLOGS_INDEX)


def ensure_auditlogs_index(index):
    if index is None:
        return None
    settings_payload = {
        'searchableAttributes': [
            'action',
            'entity_type',
            'entity_id',
            'metadata_summary',
            'user_username',
            'user_email',
            'user_full_name',
        ],
        'filterableAttributes': ['id', 'user_id', 'entity_type', 'action'],
        'sortableAttributes': ['id', 'timestamp', 'action', 'entity_type', 'entity_id'],
    }
    index.update_settings(settings_payload)
    return index


def build_auditlog_document(log):
    user = getattr(log, 'user', None)
    full_name = ''
    if user:
        first_name = getattr(user, 'first_name', '') or ''
        last_name = getattr(user, 'last_name', '') or ''
        full_name = f'{first_name} {last_name}'.strip()
    return {
        'id': log.id,
        'action': log.action,
        'entity_type': log.entity_type,
        'entity_id': log.entity_id,
        'metadata_summary': str(log.metadata or ''),
        'user_id': user.id if user else None,
        'user_username': user.username if user else '',
        'user_email': user.email if user else '',
        'user_full_name': full_name,
        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
    }


def search_auditlogs(query, offset, limit, sort=None, filter_value=None):
    index = get_auditlogs_index()
    if index is None:
        raise RuntimeError('Meilisearch client not configured')
    ensure_auditlogs_index(index)
    payload = {'offset': offset, 'limit': limit}
    if sort:
        payload['sort'] = sort
    if filter_value:
        payload['filter'] = filter_value
    return index.search(query, payload)


def upsert_auditlog(log):
    try:
        index = get_auditlogs_index()
        if index is None:
            return
        ensure_auditlogs_index(index)
        index.add_documents([build_auditlog_document(log)], primary_key='id')
    except Exception as exc:
        logger.warning('Falha ao indexar audit log no Meili: %s', exc)


def delete_auditlog(log_id):
    try:
        index = get_auditlogs_index()
        if index is None:
            return
        index.delete_document(log_id)
    except Exception as exc:
        logger.warning('Falha ao remover audit log do Meili: %s', exc)
