# crm/admin.py
from django.contrib import admin
from .models import Customer, Agent, Extension, CallLog


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'phone_number',
        'first_name',
        'last_name',
        'email',
        'company_name',
        'created_at',
    )
    search_fields = (
        'phone_number',
        'first_name',
        'last_name',
        'email',
        'company_name',
    )
    list_filter = (
        'created_at',
    )
    ordering = (
        '-created_at',
    )


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'full_name',
        'get_email',
        'extension',
    )
    search_fields = (
        'full_name',
        'user__email',
        'user__username',
    )
    
    # Custom relational getter method to display the linked auth user email securely
    def get_email(self, obj):
        if obj.user and obj.user.email:
            return obj.user.email
        return "No user email linked"
    get_email.short_description = 'Corporate Email'


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'extension_number',
        'technology',
        'created_at',
    )
    search_fields = (
        'extension_number',
    )
    list_filter = (
        'technology',
    )


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'phone_number',
        'source_number',
        'destination_number',
        'call_type',
        'customer',
        'duration',
        'billsec',
        'disposition',
        'business_disposition',
        'wrapup_completed',
        'uniqueid',
        'call_time',
    )

    search_fields = (
        'phone_number',
        'source_number',
        'destination_number',
        'uniqueid',
        'linkedid',
    )

    list_filter = (
        'call_type',
        'disposition',
        'business_disposition',
        'wrapup_completed',
        'call_time',
        'created_at',
    )

    readonly_fields = (
        'source_number',
        'destination_number',
        'billsec',
        'uniqueid',
        'linkedid',
        'raw_data',
        'created_at',
    )

    ordering = (
        '-call_time',
    )

    date_hierarchy = 'call_time'