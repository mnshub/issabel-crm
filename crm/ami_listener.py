import os
import django
import sys
import asyncio
from panoramisk import Manager
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer


# 1. Add current directory to path so it can find 'config'
sys.path.append(os.getcwd())

# 2. Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 3. Initialize Django (DO THIS BEFORE IMPORTING MODELS)
django.setup()
from crm.utils import normalize_phone_number # Make sure this is imported
from crm.models import Customer, Agent, Extension

# 1. SETUP DJANGO FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 2. NOW IMPORT MODELS
from crm.models import Customer

async def handle_events(manager, event):
    # Only process and send data if it's a DialBegin event
    if event.event == 'DialBegin':
        # Safely extract caller and destination
        raw_caller = getattr(event, 'CallerIDNum', 'unknown')
        raw_dest = getattr(event, 'DestCallerIDNum', None) or getattr(event, 'DialString', 'unknown')
        
        caller_num = normalize_phone_number(raw_caller.split('/')[-1] if '/' in raw_caller else raw_caller)
        dest_num = normalize_phone_number(raw_dest.split('/')[-1] if '/' in raw_dest else raw_dest)

        # 1. Lookup Caller (Customer or Agent)
        caller_name = "Unknown Number"
        customer = await sync_to_async(Customer.objects.filter(phone_number=caller_num).first)()
        
        if customer:
            caller_name = f"CUSTOMER: {customer.first_name} {customer.last_name}"
        else:
            agent_caller = await sync_to_async(
                Agent.objects.filter(extension__extension_number=caller_num).first
            )()
            if agent_caller:
                caller_name = f"AGENT: {agent_caller.full_name}"

        # 2. Lookup Destination Agent AND their Django User ID
        dest_name = f"Extension {dest_num}"
        target_user_id = None
        
        agent_dest = await sync_to_async(
            Agent.objects.select_related('user').filter(extension__extension_number=dest_num).first
        )()
        
        if agent_dest:
            dest_name = f"AGENT: {agent_dest.full_name}"
            if agent_dest.user:
                target_user_id = agent_dest.user.id

        # 3. Print to Terminal (Debugging)
        print("\n" + "—"*45)
        print(f"DIAL DETECTED:")
        print(f"  FROM [ {caller_name} ] ({caller_num})")
        print(f"    ---> TO [ {dest_name} ] ({dest_num})")
        
        if target_user_id:
            print(f"  ✅ TARGET FOUND: User ID {target_user_id}")
        else:
            print(f"  ⚠️ TARGET SKIPPED: No User linked to Ext {dest_num}")
        print("—"*45 + "\n")

        # 4. SEND TO BROWSER (Private Notification)
        if target_user_id:
            try:
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    f"user_{target_user_id}",
                    {
                        "type": "call_message",
                        "message": {
                            "caller": caller_name,
                            "number": caller_num,
                            "destination": dest_name,
                            "customer_id": customer.id if customer else None # For future profile linking
                        }
                    }
                )
            except Exception as e:
                print(f"  ❌ REDIS ERROR: {e}")


async def run_listener():
    manager = Manager(host='10.28.0.115', port=5038, username='django_crm', secret='Admin1234')
    
    # Register DialBegin instead of (or in addition to) Newstate
    manager.register_event('DialBegin', handle_events)
    
    try:
        await manager.connect()
        print("Connected! Monitoring live dial events...")
        await asyncio.Event().wait() 
    except Exception as e:
        print(f"Connection failed: {e}")




    try:
        await manager.connect()
        print("Connected to Issabel! Listening for calls...")
        await asyncio.Event().wait() 
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_listener())