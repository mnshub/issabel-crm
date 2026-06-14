import random
from django.core.management.base import BaseCommand
from crm.models import Customer

class Command(BaseCommand):
    help = "Seeds the database with 30+ realistic mock customers using exact Customer model fields"

    def handle(self, *args, **options):
        self.stdout.write("🏗️ Starting CRM Test Database Provisioning Pipeline...")

        # ۱. دیتای تستی برای خطوط داخلی سازمان
        internal_nodes = [
            {"phone": "101", "first": "محمد", "last": "منصوری", "email": "m.mansouri@co.com", "company": "مدیریت فنی سیستم"},
            {"phone": "102", "first": "رضا", "last": "احمدی", "email": "r.ahmadi@co.com", "company": "تیم فروش صف اول"},
            {"phone": "103", "first": "سارا", "last": "کریمی", "email": "s.karimi@co.com", "company": "پشتیبانی فنی سازمان"},
        ]

        # ۲. دیتای تستی برای نام شرکت‌های فرضی مشتریان خارجی
        mock_companies = [
            "شرکت پتروشیمی صبا", "توسعه فناوری آریا", "صنایع فولاد البرز", 
            "ارتباطات داده گستر", "گروه بازرگانی پارسیان", "نوین سیستم غرب",
            "فناوران لوتوس", "فولاد هرمزگان", "صنایع غذایی میهن", "پیشرو دیزل"
        ]

        first_names = ["علی", "حسین", "امیر", "مهدی", "مریم", "زهرا", "نازنین", "نیلوفر", "سعید", "کامران", "الهام", "جواد"]
        last_names = ["حسینی", "صادقی", "رضایی", "مرادی", "تیموری", "اکبری", "کریمیان", "هاشمی", "قاسمی", "فرهادی"]

        # تزریق خطوط داخلی
        for node in internal_nodes:
            Customer.objects.get_or_create(
                phone_number=node["phone"],
                defaults={
                    "first_name": node["first"],
                    "last_name": node["last"],
                    "email": node["email"],
                    "company_name": node["company"]
                }
            )
            self.stdout.write(f"🔹 Provisioned Internal Node Profile: {node['phone']}")

        # تولید و تزریق ۳۰ مشتری خارجی فرضی کاملاً هماهنگ با ساختار شما
        created_count = 0
        for i in range(30):
            fake_phone = f"0912{random.randint(1000000, 9999999)}"
            first = random.choice(first_names)
            last = random.choice(last_names)
            email = f"{first.lower()}_{random.randint(10,99)}@gmail.com"
            company = random.choice(mock_companies)

            customer, created = Customer.objects.get_or_create(
                phone_number=fake_phone,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "company_name": company
                }
            )
            if created:
                created_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"🎯 Success! CRM Testing Sandbox populated with {created_count} custom leads safely."))