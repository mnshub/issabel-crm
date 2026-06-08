import os
import re
import sys
import time
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
from crm.models import Extension, Customer  

LAST_IMPORT_TIME = 0
IMPORT_COOLDOWN = 4  # Seconds to wait before allowing another CDR import run


# --- Helper to identify the caller's real name ---
def get_caller_info(number):
    """Checks if a number belongs to an internal agent or a saved customer."""
    clean_num = str(number).strip()
    
    # 1. Check if it belongs to an internal Extension
    try:
        ext = Extension.objects.select_related('agent__user').get(extension_number=clean_num)
        if ext.agent and ext.agent.user:
            # Try to use First + Last name, fallback to username
            full_name = f"{ext.agent.user.first_name} {ext.agent.user.last_name}".strip()
            return full_name or ext.agent.user.username
    except Extension.DoesNotExist:
        pass

    # 2. Check if it belongs to a known Customer
    try:
        customer = Customer.objects.get(phone_number=clean_num)
        full_name = f"{customer.first_name} {customer.last_name}".strip()
        return full_name or "Known Customer"
    except Customer.DoesNotExist:
        pass

    return "Unknown Caller"
# --------------------------------------------------------

# --- Fully synchronous DB helper function ---
def get_agent_username(ext_num):
    """Safely fetches the username linked to an extension using correct model fields."""
    try:
        ext = Extension.objects.select_related('agent__user').get(extension_number=ext_num)
        agent = getattr(ext, 'agent', None)
        if agent and agent.user:
            return agent.user.username
            
    except Extension.DoesNotExist:
        return "NOT_FOUND"
    except Exception as e:
        print(f"DB Lookup Error: {e}")
    return None
# ---------------------------------------------------

async def trigger_cdr_import():
    global LAST_IMPORT_TIME
    
    # Wait for Asterisk to fully write the CDR logs to disk/database
    await asyncio.sleep(2)
    
    current_time = time.time()
    # If the last import occurred within our cooldown window, ignore this event
    if current_time - LAST_IMPORT_TIME < IMPORT_COOLDOWN:
        print("CDR import throttled to avoid duplicate concurrent executions.")
        return
        
    LAST_IMPORT_TIME = current_time
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
            clean_caller = str(caller_num).strip() 
            
            # Call the synchronous helpers safely
            agent_username = await sync_to_async(get_agent_username)(clean_dest)
            caller_name = await sync_to_async(get_caller_info)(clean_caller) 
            
            if agent_username == "NOT_FOUND":
                print(f"DEBUG: Extension '{clean_dest}' not found in CRM database. Ignoring.")
            elif agent_username:
                # THE CRITICAL FIX: Route to the Extension room, not the Agent room
                group_name = f"extension_{clean_dest}"
                print(f"DEBUG: Found agent '{agent_username}'. Sending popup to browser in room: {group_name}...")
                
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    group_name,
                    {
                        "type": "call_notification",
                        "caller": caller_name,
                        "number": clean_caller
                    }
                )
                print(f"DEBUG: WebSocket message sent successfully! (Identified: {caller_name})")
            else:
                print(f"DEBUG: Extension '{clean_dest}' exists, but has no user assigned.")

        elif message.event in ['Hangup', 'Newstate']:
            # If it's a state change, we only care if the call was answered (State: "Up")
            if message.event == 'Newstate' and getattr(message, 'channelstatedesc', '') != 'Up':
                pass # Ignore ringing or down states
            else:
                # Extract the extension number from the channel name (e.g., PJSIP/101-00001)
                channel_name = getattr(message, 'channel', '')
                match = re.search(r'(?:SIP|PJSIP)/(\d+)-', channel_name, re.IGNORECASE)
                
                if match:
                    ext_num = match.group(1)
                    clean_ext = str(ext_num).strip()
                    agent_username = await sync_to_async(get_agent_username)(clean_ext)
                    
                    # If this extension belongs to an active CRM agent, clear their popup
                    if agent_username and agent_username != "NOT_FOUND":
                        # THE CRITICAL FIX 2: Clear from the Extension room
                        group_name = f"extension_{clean_ext}"
                        print(f"DEBUG: Call Answered/Rejected for Ext {clean_ext}. Clearing popup in room: {group_name}.")
                        channel_layer = get_channel_layer()
                        await channel_layer.group_send(
                            group_name,
                            {
                                "type": "clear_notification"
                            }
                        )

            # ALWAYS trigger the CDR sync if the call has completely ended
            if message.event == 'Hangup':
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
        manager.register_event('Newstate', call_event_handler)
        
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