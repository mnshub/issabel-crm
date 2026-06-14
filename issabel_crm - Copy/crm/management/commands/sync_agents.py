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
            # Safe read-only channel connection mapping to your Issabel database settings
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
        skipped_count = 0

        try:
            with connection.cursor() as cursor:
                # Queries active extensions, technologies, and secrets from Issabel
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
                    secret = str(pbx.get('secret', '')).strip()  # Real authentication secret string token

                    if not ext_num or not full_name:
                        continue

                    # 🟢 NEW ARCHITECTURE MECHANISM: Filter out WebRTC follow-me mirrors
                    # This tells the loop to immediately skip virtual mirrors like 8101 or 8102
                    if ext_num.startswith('8'):
                        self.stdout.write(self.style.WARNING(f"⚠️ Skipping virtual WebRTC mirror line: {ext_num}"))
                        skipped_count += 1
                        continue

                    if tech not in ['SIP', 'PJSIP', 'IAX2']:
                        tech = 'PJSIP'

                    # Synchronize the primary physical/baseline line numbers cleanly in Django
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

                    # Synchronize standard web application login credentials safely
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

                    # Commit properties safely into the Agent relational table mapping
                    agent, agent_created = Agent.objects.update_or_create(
                        extension=extension,
                        defaults={
                            'user': auth_user,
                            'full_name': full_name,
                            'is_active': True
                        }
                    )
                    
                    synced_count += 1
                    self.stdout.write(f"✅ Synced Cleanly: Extension {ext_num} mapped to User '{sanitized_username}'")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync process aborted due to exception: {e}"))
        finally:
            connection.close()

        self.stdout.write(self.style.SUCCESS(
            f"🎯 Sync Pipeline Finished. Profiles provisioned: {synced_count} | Virtual lines skipped: {skipped_count}"
        ))