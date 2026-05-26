import os
import sys
import asyncio
import traceback
from panoramisk import Manager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from django.core.management import call_command
from crm.models import Extension

# --- THE FIX: Fully synchronous DB helper function ---
def get_agent_username(ext_num):
    """Safely fetches the username linked to an extension using correct model fields."""
    try:
        # Use 'agent__user' because your Extension model has a field named 'agent'
        ext = Extension.objects.select_related('agent__user').get(extension_number=ext_num)
        
        # Access the 'agent' field (not agent_profile)
        agent = getattr(ext, 'agent', None)
        if agent and agent.user:
            return agent.user.username
            
    except Extension.DoesNotExist:
        return "NOT_FOUND"
    except Exception as e:
        print(f"DB Lookup Error: {e}")
    return None# ---------------------------------------------------

async def trigger_cdr_import():
    await asyncio.sleep(2)
    try:
        print("Call ended. Auto-syncing CDR...")
        await sync_to_async(call_command)('import_cdr')
        print("Auto-sync complete.")
    except Exception as e:
        print(f"Auto-sync failed: {e}")

async def call_event_handler(manager, message):
    try:
        if message.event in ['DialBegin', 'Dial']:
            
            caller_num = getattr(message, 'calleridnum', None) or getattr(message, 'callernum', 'Unknown')
            dest_num = getattr(message, 'destcalleridnum', None) or getattr(message, 'destexten', 'Unknown')
            
            print(f"\n--- RAW RINGING EVENT ---")
            print(f"Event Type: {message.event}")
            print(f"Asterisk says Caller is: '{caller_num}'")
            print(f"Asterisk says Destination is: '{dest_num}'")
            print(f"-------------------------\n")

            if dest_num == 'Unknown':
                return

            clean_dest = str(dest_num).strip()
            
            # --- THE FIX: Call the synchronous helper safely ---
            agent_username = await sync_to_async(get_agent_username)(clean_dest)
            
            if agent_username == "NOT_FOUND":
                print(f"DEBUG: Extension '{clean_dest}' not found in CRM database. Ignoring.")
            elif agent_username:
                print(f"DEBUG: Found agent '{agent_username}'. Sending popup to browser...")
                
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    f"agent_{agent_username}",
                    {
                        "type": "call_notification",
                        "caller": "Unknown",
                        "number": str(caller_num).strip()
                    }
                )
                print("DEBUG: WebSocket message sent successfully!")
            else:
                print(f"DEBUG: Extension '{clean_dest}' exists, but has no user assigned.")

        elif message.event == 'Hangup':
            asyncio.create_task(trigger_cdr_import())

    except Exception as e:
        print(f"\n❌ FATAL ERROR IN EVENT HANDLER: {e}")
        traceback.print_exc()
        print("----------------------------------\n")

async def main():
    while True:
        manager = Manager(
            host=settings.AMI_HOST,
            port=settings.AMI_PORT,
            username=settings.AMI_USER,
            secret=settings.AMI_PASS
        )
        
        manager.register_event('DialBegin', call_event_handler)
        manager.register_event('Dial', call_event_handler)
        manager.register_event('Hangup', call_event_handler)
        
        try:
            print("Connecting to Asterisk AMI...")
            await manager.connect()
            print("Connected! Listening for events...")
            await asyncio.Event().wait() 
        except Exception as e:
            print(f"AMI Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        finally:
            manager.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down listener...")