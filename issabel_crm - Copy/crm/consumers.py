# crm/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = str(self.scope['url_route']['kwargs']['user_id'])
        self.group_name = f"user_{self.user_id}"

        try:
            # Join the group in Redis
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"✅ WS CONNECTED: User {self.user_id} joined {self.group_name}")
        except Exception as e:
            print(f"❌ REDIS ERROR: {e}")
            # If Redis fails, we still accept the socket for testing
            await self.accept() 

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except:
            pass

    async def call_message(self, event):
        await self.send(text_data=json.dumps(event['message']))