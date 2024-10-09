import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import DenyConnection, AcceptConnection


class ConsumerPermission:
    def has_object_permission(self, scope, obj):
        raise NotImplementedError

    def has_permission(self, scope):
        raise NotImplementedError


class IsAuthenticated(ConsumerPermission):
    message = "User is not authenticated"
    code = "not_authenticated"

    def has_permission(self, scope):
        user = scope.get("user", None)

        if user is None:
            return False

        return user.is_authenticated


class AllowAny(ConsumerPermission):
    def has_permission(self, scope):
        return True


class CustomAsyncWebsocketConsumer(AsyncWebsocketConsumer):
    permission_classes = [AllowAny]

    def permission_denied(self, scope, message=None, code=None):
        raise DenyConnection(message, code)

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def check_permissions(self, scope):
        for permission in self.get_permissions():
            if not permission.has_permission(scope):
                self.permission_denied(
                    scope,
                    message=getattr(permission, "message", None),
                    code=getattr(permission, "code", None),
                )

    async def websocket_connect(self, message):
        try:
            self.check_permissions(self.scope)
            await self.connect()
        except AcceptConnection:
            await self.accept()
        except DenyConnection as e:
            message, code = e.args
            # TODO reason is not accepted in this version of channels?
            await self.close(code=code)  # , reason=message)


class ChatConsumer(CustomAsyncWebsocketConsumer):
    permission_classes = [IsAuthenticated]

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",  # This is the type of message that will be sent to the group (defines the function to be called)
                "message": message,
            },
        )

    # Handler for messages sent to the group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                }
            )
        )
