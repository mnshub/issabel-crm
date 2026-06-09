# crm/management/commands/sync_agents.py
import re
import pymysql
import pymysql.err
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from crm.models import Extension, Agent

class Command(BaseCommand):
    help = "Synchronizes active agent profiles, extensions, and their passwords dynamically from Issabel PBX"

    def handle(self, *args, **kwargs):
        self.stdout.write("Connecting to Issabel PBX configuration tables...")
        
        try:
            # اتصال کاملاً ایمن و فقط‌خواندنی به دیتابیس ایزابل
            connection = pymysql.connect(
                host=settings.PBX_DB_HOST,
                user=settings.PBX_DB_USER,
                password=settings.PBX_DB_PASS,
                database='asterisk',
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.err.OperationalError as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to Issabel configuration schema: {e}"))
            return

        synced_count = 0

        try:
            with connection.cursor() as cursor:
                # اصلاح تخصصی: خواندن پسورد از جدول واقعی ایزابل که نامش 'sip' است
                cursor.execute("""
                    SELECT u.extension, u.name, d.tech, s.data AS secret
                    FROM users u
                    LEFT JOIN devices d ON u.extension = d.id
                    LEFT JOIN sip s ON u.extension = s.id AND s.keyword = 'secret'
                """)
                pbx_agents = cursor.fetchall()

                for pbx in pbx_agents:
                    ext_num = str(pbx.get('extension', '')).strip()
                    full_name = str(pbx.get('name', '')).strip()
                    tech = str(pbx.get('tech', 'PJSIP')).strip().upper()
                    secret = str(pbx.get('secret', '')).strip()  # دریافت پسورد واقعی

                    if not ext_num or not full_name:
                        continue

                    if tech not in ['SIP', 'PJSIP', 'IAX2']:
                        tech = 'PJSIP'

                    # ذخیره داینامیک داخلی به همراه پسورد واقعی در دیتابیس جنگو
                    # نام فیلد پسورد را با مدل خودتان (مثلاً password یا secret) مچ کنید
                    extension, ext_created = Extension.objects.update_or_create(
                        extension_number=ext_num,
                        defaults={
                            'technology': tech,
                            'password': secret  
                        }
                    )

                    # --- ENTERPRISE NAME SANITIZATION ENGINE ---
                    username_base = full_name.strip().replace(" ", "_").lower()
                    sanitized_username = re.sub(r'[^\w\.\+\-]', '', username_base)
                    
                    if not sanitized_username:
                        sanitized_username = f"user_{ext_num}"

                    # همگام‌سازی کاربر دیتابیس جنگو
                    auth_user, user_created = User.objects.get_or_create(
                        username=sanitized_username,
                        defaults={
                            'email': f"{sanitized_username}@company.local",
                            'is_active': True
                        }
                    )
                    
                    if user_created:
                        auth_user.set_password('Welcome@1234')
                        auth_user.save()

                    # همگام‌سازی پروفایل کارشناس
                    agent, agent_created = Agent.objects.update_or_create(
                        extension=extension,
                        defaults={
                            'user': auth_user,
                            'full_name': full_name,
                            'is_active': True
                        }
                    )
                    
                    synced_count += 1
                    self.stdout.write(f"Synced Dynamically: Extension {ext_num} -> Password Secured.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync process aborted due to exception: {e}"))
        finally:
            connection.close()

        self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {synced_count} profiles."))