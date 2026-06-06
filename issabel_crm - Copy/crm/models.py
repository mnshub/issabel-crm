from django.db import models
from .utils import normalize_phone_number
from django.contrib.auth.models import User



class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)   

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} - {self.phone_number}"

class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile', null=True, blank=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.full_name


class Extension(models.Model):
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='extension')
    extension_number = models.CharField(max_length=10, unique=True)
    secret = models.CharField(max_length=100)
    technology = models.CharField(max_length=20, default='PJSIP')  # or SIP
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.extension_number} - {self.agent.full_name}"



class CallLog(models.Model):
    CALL_TYPE_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('internal', 'Internal'),
        ('missed', 'Missed'),
        ('service', 'Service / Feature Code'),
        ('unknown', 'Unknown'),
    ]


    DISPOSITION_CHOICES = [
        ('ANSWERED', 'Answered'),
        ('NO ANSWER', 'No Answer'),
        ('BUSY', 'Busy'),
        ('FAILED', 'Failed'),
        ('CANCEL', 'Cancel'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)
    extension = models.ForeignKey(Extension, on_delete=models.SET_NULL, null=True, blank=True)
    call_type = models.CharField(max_length=10, choices=CALL_TYPE_CHOICES, default='unknown')
    phone_number = models.CharField(max_length=20)
    source_number = models.CharField(max_length=20, blank=True, null=True)
    destination_number = models.CharField(max_length=20, blank=True, null=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    billsec = models.PositiveIntegerField(default=0, help_text="Billable seconds")
    call_time = models.DateTimeField()
    recording_file = models.CharField(max_length=255, blank=True, null=True)
    disposition = models.CharField(max_length=20, choices=DISPOSITION_CHOICES, blank=True, null=True)
    uniqueid = models.CharField(max_length=50, blank=True, null=True, unique=True)
    linkedid = models.CharField(max_length=50, blank=True, null=True)
    raw_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    asterisk_id = models.CharField(max_length=100, unique=True, null=True) # To prevent duplicates
    recording_path = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)

        if self.source_number:
            self.source_number = normalize_phone_number(self.source_number)

        if self.destination_number:
            self.destination_number = normalize_phone_number(self.destination_number)

        if self.agent and not self.extension:
            try:
                self.extension = self.agent.extension
            except Extension.DoesNotExist:
                self.extension = None

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.phone_number} - {self.call_type} - {self.call_time}"

