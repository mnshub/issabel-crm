import os
from panoramisk import Manager
from django.db.models import F
from django.db.models import Q 
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
    search_num = request.GET.get('search_num')

    if extension:
        ext_num = str(extension.extension_number).strip()
        
        # Smart Query: Look for extension '101' in src, dst, or deep inside Asterisk channels!
        query = (
            Q(source_number__icontains=ext_num) | 
            Q(destination_number__icontains=ext_num) |
            Q(raw_data__channel__icontains=ext_num) |
            Q(raw_data__dstchannel__icontains=ext_num)
        )

        if search_num:
            query &= Q(phone_number__icontains=search_num)
        
        raw_calls = CallLog.objects.filter(query).order_by('-call_time')[:100]

        for call in raw_calls:
            src = str(call.source_number).strip()
            dst = str(call.destination_number).strip()
            channel = str(call.raw_data.get('channel', '')) if call.raw_data else ''

            if ext_num in src and ext_num in dst:
                continue

            # Route to respective tables based on extension presence footprint
            if ext_num in dst or (ext_num in channel and call.call_type == 'incoming'):
                inbound_calls.append(call)
            else:
                outbound_calls.append(call)

    # Fallback for Administrators without an extension profile assigned yet
    elif is_admin:
        query = Q()
        if search_num:
            query &= Q(phone_number__icontains=search_num)
            
        raw_calls = CallLog.objects.filter(query).order_by('-call_time')[:100]
        for call in raw_calls:
            if call.call_type == 'incoming':
                inbound_calls.append(call)
            else:
                outbound_calls.append(call)

    context = {
        'agent': agent_profile,
        'extension': extension,
        'is_admin': is_admin,
        'inbound_calls': inbound_calls[:10],  
        'outbound_calls': outbound_calls[:10], 
        'current_filters': request.GET 
    }
    return render(request, 'crm/agent_dashboard.html', context)


@login_required
def play_recording(request, log_id):
    call_log = CallLog.objects.filter(id=log_id).first()
    if not call_log:
        raise Http404("Recording not found.")
    
    is_admin = request.user.is_superuser or request.user.groups.filter(name='Admin').exists()
    agent_profile = getattr(request.user, 'agent_profile', None)
    agent_ext = str(agent_profile.extension.extension_number).strip() if (agent_profile and hasattr(agent_profile, 'extension')) else None

    if not is_admin:
        log_src = str(call_log.source_number).strip()
        log_dst = str(call_log.destination_number).strip()
        if not agent_ext or (agent_ext != log_src and agent_ext != log_dst):
            raise Http404("Recording not found or access denied.")

    file_path = call_log.recording_file 
    if file_path and os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), content_type='audio/wav')
    
    raise Http404("Audio file missing on server.")


async def click_to_dial(request, phone_number):
    user = await sync_to_async(lambda: request.user)()
    if not user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

    def get_extension_info():
        profile = getattr(user, 'agent_profile', None)
        if profile and hasattr(profile, 'extension'):
            return profile.extension
        return None

    extension = await sync_to_async(get_extension_info)()
    if not extension:
        return JsonResponse({'status': 'error', 'message': 'No extension assigned'}, status=400)

    tech = extension.technology 
    ext_num = str(extension.extension_number).strip()

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
            'Channel': f'{tech}/{ext_num}', 
            'Exten': phone_number,
            'Context': 'from-internal',
            'Priority': '1',
            # FIXED: Tells Asterisk your extension number is the true origin leg of this call session
            'CallerID': f"CRM Dialing <{ext_num}>", 
            'Async': 'true',
        }
        await manager.send_action(action)
        return JsonResponse({'status': 'success', 'message': 'Ringing your phone...'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        manager.close()