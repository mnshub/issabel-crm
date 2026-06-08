# crm/management/commands/sync_agents.py
import re
import pymysql
import pymysql.err
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from crm.models import Extension, Agent

class Command(BaseCommand):
    help = "Synchronizes active agent profiles and extensions directly from Issabel PBX using sanitized names as usernames"

    def handle(self, *args, **kwargs):
        self.stdout.write("Connecting to Issabel PBX configuration tables...")
        
        try:
            # Connect to Issabel's primary hardware engine database
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
                # Query user listings and map their matching device technologies
                cursor.execute("""
                    SELECT u.extension, u.name, d.tech 
                    FROM users u
                    LEFT JOIN devices d ON u.extension = d.id
                """)
                pbx_agents = cursor.fetchall()

                for pbx in pbx_agents:
                    ext_num = str(pbx.get('extension', '')).strip()
                    full_name = str(pbx.get('name', '')).strip()
                    tech = str(pbx.get('tech', 'PJSIP')).strip().upper()

                    if not ext_num or not full_name:
                        continue

                    if tech not in ['SIP', 'PJSIP', 'IAX2']:
                        tech = 'PJSIP'

                    # 1. Synchronize the Extension Table record
                    extension, ext_created = Extension.objects.update_or_create(
                        extension_number=ext_num,
                        defaults={'technology': tech}
                    )

                    # --- ENTERPRISE NAME SANITIZATION ENGINE ---
                    # Transform "Mohammad Mansouri" -> "mohammad_mansouri"
                    # Supports Persian/Arabic Unicode letter structures out of the box
                    username_base = full_name.strip().replace(" ", "_").lower()
                    
                    # Strip out any character that is not alphanumeric, a dot, a plus, a minus, or an underscore
                    # \w in Python 3 automatically matches full multi-language Unicode characters safely
                    sanitized_username = re.sub(r'[^\w\.\+\-]', '', username_base)
                    
                    # Bulletproof fallback safeguard: if name parsing yields empty strings, use extension
                    if not sanitized_username:
                        sanitized_username = f"user_{ext_num}"

                    # 2. Synchronize or create a secure Django login authentication identity user
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

                    # 3. Synchronize the Agent Table Profile layer
                    agent, agent_created = Agent.objects.update_or_create(
                        extension=extension,
                        defaults={
                            'user': auth_user,
                            'full_name': full_name,
                            'is_active': True
                        }
                    )
                    
                    synced_count += 1
                    self.stdout.write(f"Synced Identity: Extension {ext_num} -> Username: {sanitized_username} ({full_name})")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Sync process aborted due to exception: {e}"))
        finally:
            connection.close()

        self.stdout.write(self.style.SUCCESS(f"Successfully synchronized {synced_count} profiles from Issabel PBX."))