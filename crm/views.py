# crm/views.py
import os
import paramiko
from panoramisk import Manager
from django.db.models import Q 
from django.conf import settings
from .models import CallLog, Agent, Extension
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from asgiref.sync import async_to_sync

@login_required
def dashboard(request):
    is_admin = request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
    agent_profile = getattr(request.user, 'agent_profile', None)
    extension = getattr(agent_profile, 'extension', None) if agent_profile else None
    inbound_calls, outbound_calls = [], []
    search_num = request.GET.get('search_num')

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


@login_required
def play_recording(request, log_id):
    """
    Fetches the call recording file from the remote Issabel server via SFTP.
    If the recording filename is missing from the database, it performs an
    on-demand directory search using the call's unique ID.
    """
    call = get_object_or_404(CallLog, id=log_id)
    
    filename = None
    if hasattr(call, 'recording_file') and call.recording_file:
        filename = call.recording_file
    elif call.raw_data and isinstance(call.raw_data, dict):
        filename = call.raw_data.get('recordingfile') or call.raw_data.get('filename')

    filename = filename.strip() if filename else ""

    # Set up container caching path directory inside crm_web
    cache_dir = os.path.join(settings.BASE_DIR, 'media', 'recording_cache')
    os.makedirs(cache_dir, exist_ok=True)

    # If filename is known, use the fast local cache lookup path
    if filename:
        safe_cache_name = filename.replace('/', '_')
        local_file_path = os.path.join(cache_dir, f"{log_id}_{safe_cache_name}")
        if os.path.exists(local_file_path):
            response = FileResponse(open(local_file_path, 'rb'), content_type='audio/wav')
            response['Content-Disposition'] = f'inline; filename="{safe_cache_name}"'
            return response

    # Parse call date tokens to locate the targeted directory on Issabel
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

        # SCENARIO A: The filename was found in the database records
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

        # SCENARIO B: The filename column is blank (Inbound Queue Call). Search using the call UniqueID.
        if not selected_remote_path and call.uniqueid:
            target_suffix = f"{call.uniqueid}.wav"
            target_suffix_upper = f"{call.uniqueid}.WAV"
            
            # Scan both the date-sharded directory and flat folder for matches
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
            return JsonResponse({
                'status': 'error', 
                'message': f"No audio file matching unique ID '{call.uniqueid}' found on the remote server."
            }, status=404)

        # Build a safe caching filename and pull the payload down
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