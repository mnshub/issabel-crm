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

        # MATCH THE LISTENER: Use the username instead of the user ID
        self.agent_username = user.username
        self.group_name = f"agent_{self.agent_username}"

        try:
            print(f"DEBUG: Attempting to join group {self.group_name}...")
            # Join the group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"✅ WS CONNECTED: User {self.agent_username} joined {self.group_name}")
        except Exception as e:
            print(f"❌ CHANNEL LAYER ERROR: {e}")
            await self.close() # Close connection on error

    async def disconnect(self, close_code):
        print(f"DEBUG: WebSocket disconnected with code: {close_code}")
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except:
            pass

    # MATCH THE LISTENER: This method name MUST match "type": "call_notification"
    async def call_notification(self, event):
        # Extract the data sent from ami_listener.py
        caller = event.get('caller', 'Unknown')
        number = event.get('number', 'Unknown')

        # Send it down the WebSocket to the browser's JavaScript
        await self.send(text_data=json.dumps({
            'caller': caller,
            'number': number
        }))