import logging
import traceback

from channels.generic.websocket import AsyncJsonWebsocketConsumer


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
        except Exception:
            self.logger.error(
                'WS notifications connect:error\n%s',
                traceback.format_exc(),
            )
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        self.logger.info(
            'WS notifications disconnected: user=%s code=%s',
            getattr(getattr(self, 'user', None), 'id', None),
            close_code,
        )

    async def notification_created(self, event):
        await self.send_json(
            {
                'event': 'notification.created',
                'notification_id': event.get('notification_id'),
            }
        )
