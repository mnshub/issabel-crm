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

# NEW: Active memory structure tracking live answered connection vectors across event gaps
ANSWERED_CHANNELS = set()


# --- Helper to identify the caller's real name ---
def get_caller_info(number):
    """Checks if a number belongs to an internal agent or a saved customer."""
    clean_num = str(number).strip()
    
    # 1. Check if it belongs to an internal Extension
    try:
        ext = Extension.objects.select_related('agent__user').get(extension_number=clean_num)
        if ext.agent and ext.agent.user:
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
    global ANSWERED_CHANNELS
    try:
        # --- PHASE 1: RINGING INBOUND STATE HOOKS ---
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
            
            agent_username = await sync_to_async(get_agent_username)(clean_dest)
            caller_name = await sync_to_async(get_caller_info)(clean_caller) 
            
            if agent_username == "NOT_FOUND":
                print(f"DEBUG: Extension '{clean_dest}' not found in CRM database. Ignoring.")
            elif agent_username:
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

        # --- PHASE 2: LINE LEVEL STATUS HANDSHAKE MONITORS ---
        elif message.event == 'Newstate':
            channel_state = getattr(message, 'channelstatedesc', '')
            channel_name = getattr(message, 'channel', '')
            
            if channel_state == 'Up' and channel_name:
                # Store the channel string in memory to confirm the call was successfully answered
                ANSWERED_CHANNELS.add(channel_name)
                print(f"📡 Channel Connection Live: {channel_name} marked as ANSWERED (Up).")
                
                # Clear active ringing popup frames the moment the extension handset is lifted
                match = re.search(r'(?:SIP|PJSIP)/(\d+)-', channel_name, re.IGNORECASE)
                if match:
                    clean_ext = match.group(1).strip()
                    group_name = f"extension_{clean_ext}"
                    channel_layer = get_channel_layer()
                    await channel_layer.group_send(group_name, {"type": "clear_notification"})

        # --- PHASE 3: LINE DISCONNECT & POST-CALL WRAPUP INTERCEPT ROUTINES ---
        elif message.event == 'Hangup':
            channel_name = getattr(message, 'channel', '')
            
            # 1. Determine if the channel was ever successfully answered
            is_answered = channel_name in ANSWERED_CHANNELS
            ANSWERED_CHANNELS.discard(channel_name) # Evict immediately to clear memory footprints
            
            match = re.search(r'(?:SIP|PJSIP)/(\d+)-', channel_name, re.IGNORECASE)
            if match:
                clean_ext = match.group(1).strip()
                agent_username = await sync_to_async(get_agent_username)(clean_ext)
                
                if agent_username and agent_username != "NOT_FOUND":
                    group_name = f"extension_{clean_ext}"
                    channel_layer = get_channel_layer()
                    
                    # Always instruct the browser to clear layout ringing notification elements
                    await channel_layer.group_send(group_name, {"type": "clear_notification"})
                    
                    # 2. If answered, evaluate if a post-call workspace lock applies
                    if is_answered:
                        caller_id = getattr(message, 'calleridnum', '').strip()
                        connected_id = getattr(message, 'connectedlinenum', '').strip()
                        exten = getattr(message, 'exten', '').strip()
                        
                        # Isolate the outside line (the customer profile number)
                        customer_phone = connected_id if caller_id == clean_ext else caller_id
                        if not customer_phone or customer_phone == clean_ext:
                            customer_phone = exten
                            
                        if customer_phone and customer_phone != 'Unknown':
                            # Enforce Business Boundaries: Check if the other number is an internal agent extension
                            other_party_agent = await sync_to_async(get_agent_username)(customer_phone)
                            
                            if other_party_agent == "NOT_FOUND":
                                # Outside contact confirmed. Dispatch the mandatory wrap-up action frame token
                                caller_name = await sync_to_async(get_caller_info)(customer_phone)
                                print(f"🚀 Phase 3.2 Intercept: Answered external call ended for Ext {clean_ext}. Dispatching wrap-up modal lock...")
                                await channel_layer.group_send(
                                    group_name,
                                    {
                                        "type": "show_wrapup",
                                        "phone_number": customer_phone,
                                        "caller_name": caller_name
                                    }
                                )
                            else:
                                print(f"🔒 Skipped Wrap-up: Call between Ext {clean_ext} and Ext {customer_phone} was internal.")

            # Always pass control down to trigger your asynchronous flat CDR file sharding tool commands
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