# crm/management/commands/seed_test_customers.py
import random
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from crm.models import Customer, CallLog

class Command(BaseCommand):
    help = "Seeds the database with realistic external mock customers and links call logs strictly for extensions 101 and 102."

    def handle(self, *args, **options):
        self.stdout.write("🏗️ Starting CRM Test Database Provisioning Pipeline...")

        # 🟢 FIX: Automatically purge any old test logs that accidentally used extension 103
        self.stdout.write("🧹 Cleaning up any old data containing extension 103...")
        CallLog.objects.filter(source_number="103").delete()
        CallLog.objects.filter(destination_number="103").delete()

        # 1. Company and Profile Pools
        mock_companies = [
            "Saba Petrochemical Corp", "Arya Technology Solutions", "Alborz Steel Industries", 
            "Data Gostar Networking LLC", "Parsian Trading Union", "West System Technologies",
            "Lotus Advanced Innovations", "Hormozgan Casting Foundries", "Mihan Food Chains", "Pishro Diesel Automotives"
        ]

        first_names = ["Ali", "Hussein", "Amir", "Mehdi", "Maryam", "Zahra", "Nazanin", "Niloofar", "Saeed", "Kamran", "Elham", "Javad"]
        last_names = ["Hosseini", "Sadeghi", "Rezayi", "Moradi", "Teymouri", "Akbari", "Karimian", "Hashemi", "Ghasemi", "Farhadi"]
        
        # 🟢 FIX: Strictly use only your live extensions 101 and 102
        test_extensions = ["101", "102"]
        
        # Business dispositions to simulate realistic agent notes
        outcomes = [
            ('SALE_CLOSED', 'Spoke with manager. Deal closed and contract sent via email.', True),
            ('INTERESTED', 'Client requested a callback next Tuesday at 10 AM for a live hardware demo.', True),
            ('NOT_INTERESTED', 'Budget constraints. Not interested for this fiscal quarter.', True),
            ('PENDING', 'Call disconnected during transfer.', False), # wrapup_completed=False will trigger Stage 3 modals!
        ]

        # 2. Seed or Fetch Customers
        self.stdout.write("👤 Syncing Customer Profiles...")
        customers_list = []
        
        random.seed(42) # Repeatable deterministic numbers for stable generation
        for i in range(30):
            fake_phone = f"0912{1000000 + i * 2331}" 
            first = first_names[i % len(first_names)]
            last = last_names[i % len(last_names)]
            email = f"{first.lower()}_{i+10}@gmail.com"
            company = mock_companies[i % len(mock_companies)]

            customer, created = Customer.objects.get_or_create(
                phone_number=fake_phone,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "company_name": company,
                    "notes": "System Sandbox initialization contact records.\n"
                }
            )
            customers_list.append(customer)

        # 3. Generate Historical Call Logs for each Customer
        self.stdout.write("📞 Injecting Customer Telephony Logs...")
        call_logs_created = 0
        
        # Reset the seed for varied call details
        random.seed(timezone.now().timestamp())

        for customer in customers_list:
            # Check if this customer already has logs to avoid duplicating them
            if CallLog.objects.filter(customer=customer).exists():
                continue

            # Generate 3 distinct historical calls for each customer linked strictly to 101 or 102
            for call_index in range(3):
                call_type = random.choice(['incoming', 'outbound'])
                ext_num = random.choice(test_extensions)
                
                # Setup mapping fields properly based on direction
                if call_type == 'incoming':
                    src = customer.phone_number
                    dst = ext_num
                else:
                    src = ext_num
                    dst = customer.phone_number

                duration = random.randint(15, 240)
                disposition = random.choice(['ANSWERED', 'ANSWERED', 'ANSWERED', 'NO ANSWER'])
                
                if disposition == 'NO ANSWER':
                    duration = 0
                    outcome_choice = ('PENDING', 'Call was missed by agent.', True)
                else:
                    outcome_choice = random.choice(outcomes)

                # Fabricate a historical timestamp spread across the last 3 days
                past_days = random.randint(0, 3)
                past_hours = random.randint(1, 23)
                call_time = timezone.now() - datetime.timedelta(days=past_days, hours=past_hours)

                # Formulate unique Asterisk channel hashes
                unique_id_stamp = f"{int(call_time.timestamp())}.{random.randint(100000, 999999)}"
                mock_recording = f"exten-{ext_num}-{customer.phone_number}-{call_time.strftime('%Y%m%d-%H%M%S')}-{unique_id_stamp}.wav"

                # Commit strictly to Database models
                CallLog.objects.create(
                    customer=customer,
                    call_type=call_type,
                    phone_number=customer.phone_number,
                    source_number=src,
                    destination_number=dst,
                    duration=duration,
                    billsec=max(0, duration - random.randint(2, 5)) if duration > 0 else 0,
                    call_time=call_time,
                    disposition=disposition,
                    business_disposition=outcome_choice[0],
                    notes=outcome_choice[1],
                    wrapup_completed=outcome_choice[2],
                    uniqueid=unique_id_stamp,
                    recording_file=mock_recording,
                    raw_data={
                        "channel": f"PJSIP/{ext_num}-000000ab",
                        "dstchannel": f"PJSIP/{customer.phone_number}-000000ac"
                    }
                )
                call_logs_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"🎯 Success! Generated 30 Customers and {call_logs_created} structured Call Logs for Ext 101/102 safely."
        ))