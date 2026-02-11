import asyncio
import logging
import traceback

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .services.presence import (
    get_presence_recipient_ids,
    mark_user_offline,
    mark_user_online,
    touch_last_seen,
)


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    logger = logging.getLogger(__name__)

    async def connect(self):
        try:
            path = self.scope.get('path')
            query_string = self.scope.get('query_string')
            user = self.scope.get('user')
            jwt_invalid = self.scope.get('jwt_invalid')
            jwt_reason = self.scope.get('jwt_invalid_reason')
            self.logger.info(
                'WS notifications connect:start path=%s qs=%s user=%s auth=%s jwt_invalid=%s reason=%s',
                path,
                query_string,
                getattr(user, 'id', None),
                getattr(user, 'is_authenticated', False),
                jwt_invalid,
                jwt_reason,
            )
            if not user or not user.is_authenticated or jwt_invalid:
                self.logger.info(
                    'WS notifications auth:fail user=%s auth=%s jwt_invalid=%s reason=%s',
                    getattr(user, 'id', None),
                    getattr(user, 'is_authenticated', False),
                    jwt_invalid,
                    jwt_reason,
                )
                await self.close(code=4401)
                return

            self.user = user
            self.group_name = f'user_{user.id}'
            self.logger.info('WS notifications group_add:before group=%s', self.group_name)
            if not self.channel_layer:
                self.logger.error('WS notifications no channel_layer available')
                await self.close(code=1011)
                return
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            self.logger.info('WS notifications group_add:after group=%s', self.group_name)
            self.logger.info('WS notifications accept:before user=%s', user.id)
            await self.accept()
            self.logger.info('WS notifications accept:after user=%s', user.id)
            await self._handle_presence_online()
        except Exception:
            self.logger.error(
                'WS notifications connect:error\n%s',
                traceback.format_exc(),
            )
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        try:
            if getattr(getattr(self, 'user', None), 'is_authenticated', False):
                await self._handle_presence_offline()
        except Exception:
            self.logger.error(
                'WS notifications disconnect:presence_error\n%s',
                traceback.format_exc(),
            )
        self.logger.info(
            'WS notifications disconnected: user=%s code=%s',
            getattr(getattr(self, 'user', None), 'id', None),
            close_code,
        )

    async def receive_json(self, content, **kwargs):
        event = content.get('event')
        if event in {'presence.heartbeat', 'presence.ping'}:
            await self._handle_presence_heartbeat()
            return

    async def notification_created(self, event):
        await self.send_json(
            {
                'event': 'notification.created',
                'notification_id': event.get('notification_id'),
            }
        )

    async def presence_event(self, event):
        await self.send_json(
            {
                'event': event.get('event'),
                'user_id': event.get('user_id'),
                'last_seen_at': event.get('last_seen_at'),
                'is_online': event.get('is_online'),
            }
        )

    async def _handle_presence_online(self):
        now = timezone.now()
        await database_sync_to_async(mark_user_online)(self.user.id, now=now)
        await database_sync_to_async(touch_last_seen)(self.user, now=now, force=False)
        await self._broadcast_presence_event('user_online', now, True)

    async def _handle_presence_heartbeat(self):
        now = timezone.now()
        await database_sync_to_async(mark_user_online)(self.user.id, now=now)
        await database_sync_to_async(touch_last_seen)(self.user, now=now, force=False)

    async def _handle_presence_offline(self):
        now = timezone.now()
        await database_sync_to_async(mark_user_offline)(self.user.id)
        await database_sync_to_async(touch_last_seen)(self.user, now=now, force=True)
        await self._broadcast_presence_event('user_offline', now, False)

    async def _broadcast_presence_event(self, event_name, now, is_online):
        if not self.channel_layer:
            return
        recipient_ids = await database_sync_to_async(get_presence_recipient_ids)(self.user)
        payload = {
            'type': 'presence.event',
            'event': event_name,
            'user_id': self.user.id,
            'last_seen_at': now.isoformat(),
            'is_online': is_online,
        }
        await asyncio.gather(
            *[
                self.channel_layer.group_send(f'user_{recipient_id}', payload)
                for recipient_id in recipient_ids
            ]
        )
