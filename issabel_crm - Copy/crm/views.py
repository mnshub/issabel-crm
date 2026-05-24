from django.shortcuts import render
from django.contrib.auth.decorators import login_required


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    """
    Main entry point for the CRM. 
    Redirects Admins to a broad overview and Agents to their personal workspace.
    """
    # 1. Determine the user's role
    is_admin = request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
    
    # 2. Get the Agent profile and Extension linked to this user
    # We use getattr to safely handle users who might not have a profile yet
    agent_profile = getattr(request.user, 'agent_profile', None)
    extension = None
    
    if agent_profile:
        # Check if this agent has a physical extension assigned in the Admin panel
        extension = getattr(agent_profile, 'extension', None)

    # 3. Prepare the data for the template
    context = {
        'agent': agent_profile,
        'extension': extension,
        'is_admin': is_admin,
    }

    # 4. Route to the correct template
    if is_admin:
        # If you haven't created admin_dashboard.html yet, 
        # you can use agent_dashboard.html for both for now.
        return render(request, 'crm/agent_dashboard.html', context)
    else:
        return render(request, 'crm/agent_dashboard.html', context)