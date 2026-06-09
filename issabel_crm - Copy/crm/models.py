# crm/models.py
from django.db import models
from django.contrib.auth.models import User

class Extension(models.Model):
    TECHNOLOGY_CHOICES = [
        ('SIP', 'SIP'),
        ('PJSIP', 'PJSIP'),
        ('IAX2', 'IAX2'),
    ]
    extension_number = models.CharField(max_length=10, unique=True, help_text="Asterisk internal extension number")
    technology = models.CharField(max_length=10, choices=TECHNOLOGY_CHOICES, default='PJSIP')
    created_at = models.DateTimeField(auto_now_add=True)
    password = models.CharField(max_length=100, blank=True, default="", help_text="PJSIP secret key for WebRTC registration")

    def __str__(self):
        return f"{self.technology}/{self.extension_number}"


class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile', null=True, blank=True)
    full_name = models.CharField(max_length=100)
    extension = models.OneToOneField(Extension, on_delete=models.SET_NULL, null=True, blank=True, related_name='agent')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Customer(models.Model):
    phone_number = models.CharField(max_length=30, unique=True, help_text="Normalized unique phone number string")
    first_name = models.CharField(max_length=50, blank=True, default="")
    last_name = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    company_name = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.phone_number


class CallLog(models.Model):
    CALL_TYPE_CHOICES = [
        ('incoming', 'Incoming'),
        ('outbound', 'Outbound'),
        ('internal', 'Internal'),
    ]

    BUSINESS_DISPOSITION_CHOICES = [
        ('PENDING', 'Pending Wrap-up'),
        ('SALE_CLOSED', 'Sale Closed / Deal Won'),
        ('INTERESTED', 'Interested / Follow-up Scheduled'),
        ('NOT_INTERESTED', 'Not Interested / Refused'),
        ('SPAM', 'Spam / Wrong Number'),
        ('INTERNAL_WORK', 'Internal Operations'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    call_type = models.CharField(max_length=12, choices=CALL_TYPE_CHOICES)
    
    # Raw target columns
    phone_number = models.CharField(max_length=30)
    source_number = models.CharField(max_length=30)
    destination_number = models.CharField(max_length=30)
    duration = models.IntegerField(default=0)
    billsec = models.IntegerField(default=0)
    call_time = models.DateTimeField()
    disposition = models.CharField(max_length=20, default='UNKNOWN')
    business_disposition = models.CharField(max_length=30, choices=BUSINESS_DISPOSITION_CHOICES, default='PENDING')
    wrapup_completed = models.BooleanField(default=False)
    
    # UniqueID automatically builds a Unique B-Tree Index in Postgres via unique=True
    uniqueid = models.CharField(max_length=40, unique=True)
    linkedid = models.CharField(max_length=40, blank=True, null=True)
    recording_file = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    raw_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- ADVANCED POSTGRESQL TUNING META ENGINE ---
    class Meta:
        indexes = [
            # 1. Composite Index: Speeds up dashboard loading by filtering and sorting call logs simultaneously
            models.Index(fields=['phone_number', '-call_time'], name='crm_call_phone_time_idx'),
            
            # 2. Composite Index: Speeds up agent metric queries on the dashboard log display grids
            models.Index(fields=['call_type', '-call_time'], name='crm_call_type_time_idx'),
            
            # 3. Partial Index: Only indexes calls pending a wrap-up. This keeps index sizes small and performant.
            models.Index(
                fields=['wrapup_completed'], 
                name='crm_call_wrapup_pending_idx',
                condition=models.Q(wrapup_completed=False)
            ),
        ]

    def __str__(self):
        return f"{self.call_type.upper()} | {self.source_number} -> {self.destination_number}"