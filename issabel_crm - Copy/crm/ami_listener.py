import os
import django
import sys
import asyncio
from panoramisk import Manager
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer

# 1. Environment Setup
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 2. Imports after setup
from crm.utils import normalize_phone_number
from crm.models import Customer, Agent

async def handle_events(manager, event):
    if event.event == 'DialBegin':
        raw_caller = getattr(event, 'CallerIDNum', 'unknown')
        raw_dest = getattr(event, 'DestCallerIDNum', None) or getattr(event, 'DialString', 'unknown')
        
        caller_num = normalize_phone_number(raw_caller.split('/')[-1] if '/' in raw_caller else raw_caller)
        dest_num = normalize_phone_number(raw_dest.split('/')[-1] if '/' in raw_dest else raw_dest)

        # Lookup logic
        caller_name = "Unknown"
        customer = await sync_to_async(lambda: Customer.objects.filter(phone_number=caller_num).first())()
        
        if customer:
            caller_name = f"CUSTOMER: {customer.first_name} {customer.last_name}"
        else:
            agent_caller = await sync_to_async(lambda: Agent.objects.filter(extension__extension_number=caller_num).first())()
            if agent_caller:
                caller_name = f"AGENT: {agent_caller.full_name}"

        # Target lookup
        agent_dest = await sync_to_async(lambda: Agent.objects.select_related('user').filter(extension__extension_number=dest_num).first())()
        
        if agent_dest and agent_dest.user:
            target_user_id = agent_dest.user.id
            print(f"DEBUG: Notifying Agent {agent_dest.full_name} (User {target_user_id})")
            
            try:
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    f"user_{target_user_id}",
                    {
                        "type": "call_message",
                        "message": {
                            "caller": caller_name,
                            "number": caller_num,
                            "status": "ringing"
                        }
                    }
                )
            except Exception as e:
                print(f"❌ WS ERROR: {e}. Check if Redis is running.")

async def run_listener():
    # Update these with your actual Issabel credentials
    manager = Manager(host='10.28.0.115', port=5038, username='django_crm', secret='Admin1234')
    manager.register_event('DialBegin', handle_events)
    
    try:
        await manager.connect()
        print("✅ Monitoring live Issabel events...")
        await asyncio.Event().wait() 
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_listener())