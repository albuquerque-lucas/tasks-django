from auditlogs.utils import log_audit_event
from notifications.utils import notify


def log_team_create(request, team):
    log_audit_event(
        request,
        action='team.create',
        entity_type='Team',
        entity_id=team.id,
        metadata={
            'name': team.name,
            'description': team.description,
        },
    )


def log_team_update(request, team, before, after):
    changes = {
        key: {'from': before[key], 'to': after[key]}
        for key in before
        if before[key] != after[key]
    }
    if changes:
        log_audit_event(
            request,
            action='team.update',
            entity_type='Team',
            entity_id=team.id,
            metadata={'changes': changes},
        )
    return changes


def log_team_delete(request, team):
    log_audit_event(
        request,
        action='team.delete',
        entity_type='Team',
        entity_id=team.id,
        metadata={
            'name': team.name,
            'description': team.description,
        },
    )


def log_members_changed(request, team, added_members, removed_members):
    if added_members:
        log_audit_event(
            request,
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
                    'actor_id': request.user.id,
                },
                actor=request.user,
            )
    if removed_members:
        log_audit_event(
            request,
            action='team.members.remove',
            entity_type='Team',
            entity_id=team.id,
            metadata={'member_ids': removed_members},
        )


def log_managers_changed(request, team, added_managers, removed_managers):
    if added_managers:
        log_audit_event(
            request,
            action='team.managers.add',
            entity_type='Team',
            entity_id=team.id,
            metadata={'manager_ids': added_managers},
        )
    if removed_managers:
        log_audit_event(
            request,
            action='team.managers.remove',
            entity_type='Team',
            entity_id=team.id,
            metadata={'manager_ids': removed_managers},
        )
