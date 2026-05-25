from django.contrib import admin
from .models import Customer, Agent, Extension, CallLog


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'first_name',
        'last_name',
        'phone_number',
        'email',
        'company',
        'created_at',
    )
    search_fields = (
        'first_name',
        'last_name',
        'phone_number',
        'email',
        'company',
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
        'email',
        'is_active',
        'created_at',
    )
    search_fields = (
        'full_name',
        'email',
    )
    list_filter = (
        'is_active',
        'created_at',
    )
    ordering = (
        '-created_at',
    )


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'extension_number',
        'agent',
        'technology',
        'is_active',
    )
    search_fields = (
        'extension_number',
        'agent__full_name',
    )
    list_filter = (
        'technology',
        'is_active',
    )


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'phone_number',
        'source_number',
        'destination_number',
        'call_type',
        'agent',
        'extension',
        'duration',
        'billsec',
        'disposition',
        'uniqueid',
        'call_time',
    )

    search_fields = (
        'phone_number',
        'source_number',
        'destination_number',
        'agent__full_name',
        'uniqueid',
        'linkedid',
    )

    list_filter = (
        'call_type',
        'disposition',
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

    exclude = (
        'extension',
    )

    ordering = (
        '-call_time',
    )

    date_hierarchy = 'call_time'
