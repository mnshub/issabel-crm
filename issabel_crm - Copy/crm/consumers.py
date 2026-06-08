import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return

        # Dynamically find the extension to join the correct room
        try:
            from crm.models import Agent
            agent = await sync_to_async(Agent.objects.select_related('extension').get)(user=self.user)
            ext_num = agent.extension.extension_number
            self.group_name = f"extension_{ext_num}"
        except Exception as e:
            print(f"DEBUG Consumer: Could not find extension for {self.user.username}: {e}")
            self.group_name = f"agent_{self.user.username}" # Fallback

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"✅ WS CONNECTED: User {self.user.username} joined {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # --- THE HANDLERS: These catch the listener's messages and push them to the browser ---

    async def call_notification(self, event):
        """Catches 'call_notification' from AMI Listener and sends it to JS"""
        print(f"DEBUG Consumer: Pushing RINGING event to browser for {self.group_name}")
        await self.send(text_data=json.dumps({
            'type': 'call_ringing', 
            'caller': event.get('caller', 'Unknown'),
            'number': event.get('number', 'Unknown')
        }))

    async def clear_notification(self, event):
        """Catches 'clear_notification' from AMI Listener and sends it to JS"""
        print(f"DEBUG Consumer: Pushing CLEAR event to browser for {self.group_name}")
        await self.send(text_data=json.dumps({
            'type': 'clear_notification'
        }))