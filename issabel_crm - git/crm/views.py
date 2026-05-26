import os
from panoramisk import Manager
from django.db.models import F
from django.db.models import Q  # This allows us to use 'Q' directly
from django.conf import settings
from .models import CallLog, Agent
from django.shortcuts import render
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    is_admin = request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
    agent_profile = getattr(request.user, 'agent_profile', None)
    extension = getattr(agent_profile, 'extension', None) if agent_profile else None

    inbound_calls = []
    outbound_calls = []

    if extension:
        ext_num = str(extension.extension_number).strip()
        
        # 1. Fetch calls where this agent is either the source or destination
        query = Q(source_number=ext_num) | Q(destination_number=ext_num)

        # Apply filters from search bar/dropdowns
        search_num = request.GET.get('search_num')
        if search_num:
            query &= Q(phone_number__icontains=search_num)
        
        # Get the raw results
        raw_calls = CallLog.objects.filter(query).order_by('-call_time')[:40]

        # 2. Python-level scrubbing and separation
        for call in raw_calls:
            src = str(call.source_number).strip()
            dst = str(call.destination_number).strip()

            # COMPLETELY IGNORE calls where agent is both source and destination
            if src == ext_num and dst == ext_num:
                continue

            # Separate into lists
            if dst == ext_num:
                inbound_calls.append(call)
            elif src == ext_num:
                outbound_calls.append(call)

    context = {
        'agent': agent_profile,
        'extension': extension,
        'is_admin': is_admin,
        'inbound_calls': inbound_calls[:10],  # Show top 10 inbound
        'outbound_calls': outbound_calls[:10], # Show top 10 outbound
        'current_filters': request.GET 
    }
    return render(request, 'crm/agent_dashboard.html', context)


@login_required
def play_recording(request, log_id):
    call_log = CallLog.objects.filter(id=log_id).first()
    
    # Security: Ensure the agent only accesses their own recordings or is an admin
    if not call_log or (not request.user.is_superuser and call_log.destination_number != request.user.agent_profile.extension.extension_number):
        raise Http404("Recording not found or access denied.")

    # In a real setup, this path comes from your Issabel server
    # For now, we assume the path stored in 'recording_file' is accessible
    file_path = call_log.recording_file 
    
    if file_path and os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), content_type='audio/wav')
    
    raise Http404("Audio file missing on server.")


async def click_to_dial(request, phone_number):
    # 1. Safely get the user and agent profile in an async-friendly way
    user = await sync_to_async(lambda: request.user)()
    
    def get_extension_info():
        profile = getattr(user, 'agent_profile', None)
        if profile and hasattr(profile, 'extension'):
            return profile.extension
        return None

    extension = await sync_to_async(get_extension_info)()

    if not extension:
        return JsonResponse({'status': 'error', 'message': 'No extension assigned'}, status=400)

    # FIX: Define 'tech' and 'ext_num' here before they are used below
    tech = extension.technology  # This will be 'SIP' or 'PJSIP'
    ext_num = extension.extension_number

    manager = Manager(
    host=settings.AMI_HOST, 
    port=settings.AMI_PORT, 
    username=settings.AMI_USER, 
    secret=settings.AMI_PASS
    )
    
    try:
        await manager.connect()
        action = {
            'Action': 'Originate',
            'Channel': f'{tech}/{ext_num}', # Now 'tech' is defined!
            'Exten': phone_number,
            'Context': 'from-internal',
            'Priority': '1',
            'CallerID': f"Calling: {phone_number} <{phone_number}>",
            'Async': 'true',
        }
        await manager.send_action(action)
        return JsonResponse({'status': 'success', 'message': 'Ringing your phone...'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        manager.close()