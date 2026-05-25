# crm/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("DEBUG: Connection initiated...")
        
        # Check the user
        user = self.scope.get('user')
        print(f"DEBUG: User in WebSocket scope is: {user}")
        
        # Reject unauthenticated connections
        if not user or user.is_anonymous:
            print("DEBUG: Connection rejected - User is Anonymous. Check your session/cookies.")
            await self.close()
            return

        self.user_id = str(user.id)
        self.group_name = f"user_{self.user_id}"

        try:
            print(f"DEBUG: Attempting to join group {self.group_name}...")
            # Join the group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"✅ WS CONNECTED: User {self.user_id} joined {self.group_name}")
        except Exception as e:
            print(f"❌ CHANNEL LAYER ERROR: {e}")
            await self.accept() 

    async def disconnect(self, close_code):
        print(f"DEBUG: WebSocket disconnected with code: {close_code}")
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except:
            pass

    async def call_message(self, event):
        await self.send(text_data=json.dumps(event['message']))