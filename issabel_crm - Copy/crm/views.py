# crm/views.py
import os
import json
import paramiko
from panoramisk import Manager
from django.db.models import Q 
from django.conf import settings
from .models import CallLog, Agent, Extension, Customer
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from asgiref.sync import async_to_sync

@login_required
def dashboard(request):
    """
    Renders the agent workspace dashboard, partitioning traffic into inbound 
    and outbound queues while resolving raw extensions to agent names safely.
    """
    is_admin = request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
    agent_profile = getattr(request.user, 'agent_profile', None)
    extension = getattr(agent_profile, 'extension', None) if agent_profile else None
    inbound_calls, outbound_calls = [], []
    search_num = request.GET.get('search_num')

    # FIX: Loop through Agents with extensions instead of Extensions with agents.
    # This prevents the RelatedObjectDoesNotExist crash entirely.
    agents_pool = Agent.objects.select_related('extension').filter(extension__isnull=False)
    ext_map = {agent.extension.extension_number: agent.full_name for agent in agents_pool}
    
    customers_pool = Customer.objects.all()
    cust_map = {c.phone_number: f"{c.first_name} {c.last_name or ''}".strip() for c in customers_pool}

    if extension:
        ext_num = str(extension.extension_number).strip()
        query = (Q(source_number__icontains=ext_num) | Q(destination_number__icontains=ext_num) |
                 Q(raw_data__channel__icontains=ext_num) | Q(raw_data__dstchannel__icontains=ext_num))
        if search_num: 
            query &= Q(phone_number__icontains=search_num)
        
        raw_calls = CallLog.objects.filter(query).order_by('-call_time')[:100]
        
        for call in raw_calls:
            src = str(call.source_number).strip()
            dst = str(call.destination_number).strip()
            dstchannel = str(call.raw_data.get('dstchannel', '')) if call.raw_data else ''

            if ext_num == src and ext_num == dst: 
                continue

            # Assign display name attributes dynamically based on our cache map
            call.source_display = ext_map.get(src) or cust_map.get(src) or src
            call.destination_display = ext_map.get(dst) or cust_map.get(dst) or dst

            if call.call_type == 'incoming':
                inbound_calls.append(call)
            elif call.call_type == 'outbound':
                outbound_calls.append(call)
            else:
                if ext_num in dst or ext_num in dstchannel:
                    inbound_calls.append(call)
                else:
                    outbound_calls.append(call)
                    
    elif is_admin:
        query = Q()
        if search_num: 
            query &= Q(phone_number__icontains=search_num)
        raw_calls = CallLog.objects.filter(query).order_by('-call_time')[:100]
        for call in raw_calls:
            src = str(call.source_number).strip()
            dst = str(call.destination_number).strip()
            call.source_display = ext_map.get(src) or cust_map.get(src) or src
            call.destination_display = ext_map.get(dst) or cust_map.get(dst) or dst
            inbound_calls.append(call)

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
def customer_lookup(request, phone_number):
    """
    Identity Lookup Endpoint: Checks both internal corporate extensions 
    and external customer tables to build a clear interaction history.
    """
    clean_number = phone_number.strip()
    
    # Check internal colleague status
    internal_ext = Extension.objects.select_related('agent').filter(extension_number=clean_number).first()
    
    history_queryset = CallLog.objects.filter(
        Q(phone_number=clean_number) | Q(source_number=clean_number) | Q(destination_number=clean_number)
    ).order_by('-call_time')[:50]
    
    timeline_data = []
    for log in history_queryset:
        formatted_time = log.call_time.strftime('%Y-%m-%d %H:%M')
        timeline_data.append({
            'id': log.id,
            'call_type': log.call_type,
            'source': log.source_number,
            'destination': log.destination_number,
            'duration': f"{log.duration}s" if log.disposition == 'ANSWERED' else '---',
            'disposition': log.disposition,
            'call_time': formatted_time
        })

    if internal_ext:
        return JsonResponse({
            'status': 'agent',
            'phone_number': clean_number,
            'full_name': internal_ext.agent.full_name if internal_ext.agent else f"Extension {clean_number}",
            'email': internal_ext.agent.user.email if (internal_ext.agent and internal_ext.agent.user) else 'No corporate email profile.',
            'company': 'Internal Corporate Colleague',
            'timeline': timeline_data
        })

    # Look up external customers if it's not an internal extension
    customer = Customer.objects.filter(phone_number=clean_number).first()
    
    if not customer:
        return JsonResponse({
            'status': 'not_found',
            'phone_number': clean_number,
            'timeline': timeline_data
        })

    return JsonResponse({
        'status': 'success',
        'customer_id': customer.id,
        'phone_number': customer.phone_number,
        'first_name': customer.first_name,
        'last_name': customer.last_name or '',
        'email': customer.email or '',
        'company': customer.company_name or 'Private Account',
        'timeline': timeline_data
    })


@login_required
def save_customer(request):
    """
    API Mutation Endpoint: Receives AJAX POST requests to create or update
    a master customer registry profile, then retroactively links matching call logs.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid HTTP request method.'}, status=405)
    
    try:
        data = json.loads(request.body)
        phone_num = data.get('phone_number', '').strip()
        
        if not phone_num:
            return JsonResponse({'status': 'error', 'message': 'Phone number field is mandatory.'}, status=400)
        
        customer, created = Customer.objects.update_or_create(
            phone_number=phone_num,
            defaults={
                'first_name': data.get('first_name', '').strip(),
                'last_name': data.get('last_name', '').strip(),
                'email': data.get('email', '').strip(),
                'company_name': data.get('company_name', '').strip(),
            }
        )
        
        # Retroactively map all past flat call logs to this profile row
        CallLog.objects.filter(phone_number=phone_num).update(customer=customer)
        
        return JsonResponse({
            'status': 'success',
            'message': f"Customer record successfully {'created' if created else 'updated'}!",
            'customer_id': customer.id
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Database fault: {str(e)}"}, status=500)


@login_required
def play_recording(request, log_id):
    """
    Fetches the call recording file from the remote Issabel server via SFTP,
    caches it locally to support browser range requests, and streams it.
    """
    call = get_object_or_404(CallLog, id=log_id)
    filename = call.recording_file.strip() if call.recording_file else ""
    
    if not filename and call.raw_data and isinstance(call.raw_data, dict):
        filename = call.raw_data.get('recordingfile') or call.raw_data.get('filename') or ""

    cache_dir = os.path.join(settings.BASE_DIR, 'media', 'recording_cache')
    os.makedirs(cache_dir, exist_ok=True)

    if filename:
        safe_cache_name = filename.replace('/', '_')
        local_file_path = os.path.join(cache_dir, f"{log_id}_{safe_cache_name}")
        if os.path.exists(local_file_path):
            response = FileResponse(open(local_file_path, 'rb'), content_type='audio/wav')
            response['Content-Disposition'] = f'inline; filename="{safe_cache_name}"'
            return response

    call_date = call.call_time
    year = call_date.strftime('%Y')
    month = call_date.strftime('%m')
    day = call_date.strftime('%d')

    sharded_remote_dir = f"/var/spool/asterisk/monitor/{year}/{month}/{day}"
    flat_remote_dir = "/var/spool/asterisk/monitor"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    selected_remote_path = None

    try:
        ssh.connect(
            hostname=getattr(settings, 'PBX_SSH_HOST', '192.168.100.115'),
            port=int(getattr(settings, 'PBX_SSH_PORT', 22)),
            username=getattr(settings, 'PBX_SSH_USER', 'root'),
            password=getattr(settings, 'PBX_SSH_PASS', ''),
            timeout=10
        )
        sftp = ssh.open_sftp()

        if filename:
            base_name, ext = os.path.splitext(filename)
            filenames_to_try = [filename, f"{base_name}.wav", f"{base_name}.WAV"]
            possible_paths = []
            for fname in filenames_to_try:
                if "/" in fname:
                    possible_paths.append(f"/var/spool/asterisk/monitor/{fname.lstrip('/')}")
                else:
                    possible_paths.append(f"{sharded_remote_dir}/{fname}")
                    possible_paths.append(f"{flat_remote_dir}/{fname}")

            for remote_path in possible_paths:
                try:
                    sftp.stat(remote_path)
                    selected_remote_path = remote_path
                    break
                except IOError:
                    continue

        if not selected_remote_path and call.uniqueid:
            target_suffix = f"{call.uniqueid}.wav"
            target_suffix_upper = f"{call.uniqueid}.WAV"
            
            for search_directory in [sharded_remote_dir, flat_remote_dir]:
                try:
                    file_list = sftp.listdir(search_directory)
                    for f in file_list:
                        if f.endswith(target_suffix) or f.endswith(target_suffix_upper) or call.uniqueid in f:
                            selected_remote_path = f"{search_directory}/{f}"
                            filename = f
                            break
                    if selected_remote_path:
                        break
                except IOError:
                    continue

        if not selected_remote_path:
            sftp.close()
            ssh.close()
            return JsonResponse({'status': 'error', 'message': f"No audio file discovered for unique ID '{call.uniqueid}'."}, status=404)

        safe_cache_name = filename.replace('/', '_')
        local_file_path = os.path.join(cache_dir, f"{log_id}_{safe_cache_name}")

        sftp.get(selected_remote_path, local_file_path)
        sftp.close()
        ssh.close()

        response = FileResponse(open(local_file_path, 'rb'), content_type='audio/wav')
        response['Content-Disposition'] = f'inline; filename="{safe_cache_name}"'
        return response

    except Exception as err:
        try: ssh.close()
        except Exception: pass
        return JsonResponse({'status': 'error', 'message': f"SFTP audio download failed: {str(err)}"}, status=500)


async def _async_originate_call(tech, ext_num, clean_phone, caller_id_string):
    manager = Manager(host=settings.AMI_HOST, port=settings.AMI_PORT, username=settings.AMI_USER, secret=settings.AMI_PASS)
    await manager.connect()
    action = {'Action': 'Originate', 'Channel': f'{tech}/{ext_num}', 'Exten': clean_phone, 'Context': 'from-internal',
              'Priority': '1', 'CallerID': caller_id_string, 'Async': 'true', 'Variable': f'__AMPUSER={ext_num}'}
    await manager.send_action(action)
    manager.close()


@login_required
def click_to_dial(request, phone_number):
    user = request.user
    agent_profile = getattr(user, 'agent_profile', None)
    if not agent_profile or not hasattr(agent_profile, 'extension'):
        return JsonResponse({'status': 'error', 'message': 'No extension assigned to your profile.'}, status=400)
    extension = agent_profile.extension
    tech, ext_num = extension.technology, str(extension.extension_number).strip()
    clean_phone = phone_number.strip()
    is_internal = clean_phone.isdigit() and (len(clean_phone) <= 5)
    display_name = agent_profile.full_name if is_internal else "XYZ"
    caller_id_string = f'"{display_name} to {clean_phone}" <{ext_num}>'
    try:
        async_to_sync(_async_originate_call)(tech, ext_num, clean_phone, caller_id_string)
        return JsonResponse({'status': 'success', 'message': f'Calling {clean_phone}...'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"VoIP error: {str(e)}"}, status=500)