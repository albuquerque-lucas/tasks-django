from auditlogs.utils import log_audit_event
from notifications.utils import notify


def log_task_create(request, task):
    log_audit_event(
        request,
        action='task.create',
        entity_type='Task',
        entity_id=task.id,
        metadata={
            'title': task.title,
            'user_id': task.user_id,
            'team_id': task.team_id,
            'priority_level_id': task.priority_level_id,
            'status': task.status,
        },
    )


def log_task_update(request, task, before, after):
    changes = {
        key: {'from': before[key], 'to': after[key]}
        for key in before
        if before[key] != after[key]
    }
    if changes:
        log_audit_event(
            request,
            action='task.update',
            entity_type='Task',
            entity_id=task.id,
            metadata={'changes': changes},
        )
    return changes


def log_task_delete(request, task):
    log_audit_event(
        request,
        action='task.delete',
        entity_type='Task',
        entity_id=task.id,
        metadata={
            'title': task.title,
            'user_id': task.user_id,
            'team_id': task.team_id,
            'priority_level_id': task.priority_level_id,
            'status': task.status,
        },
    )


def notify_task_assigned(request_user, task):
    notify(
        recipient=task.user,
        type='task.assigned',
        payload={
            'task_id': task.id,
            'team_id': task.team_id,
            'actor_id': request_user.id,
        },
        actor=request_user,
    )
