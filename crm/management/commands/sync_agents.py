import pymysql
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from crm.models import Agent, Extension
from django.conf import settings

class Command(BaseCommand):
    help = "Sync Agents and Extensions from Issabel and link to Django Users"

    def handle(self, *args, **kwargs):
        try:
            connection = pymysql.connect(
                host=settings.PBX_DB_HOST,
                user=settings.PBX_DB_USER,
                password=settings.PBX_DB_PASS,
                database='asterisk', # Note: keep 'asteriskcdrdb' for the import_cdr script!
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection failed: {e}"))
            return

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT extension, name FROM users")
                rows = cursor.fetchall()

                for row in rows:
                    ext_num = str(row['extension'])
                    real_name = row['name']
                    
                    # 1. Ensure a Django User exists for this extension
                    # We use the extension number as the username to prevent duplicates
                    user, created = User.objects.get_or_create(
                        username=f"user_{ext_num}",
                        defaults={'is_active': True}
                    )
                    if created:
                        user.set_password('Welcome123!') # Set a default password
                        user.save()

                    # 2. Update or Create the Agent and link to the User
                    agent, _ = Agent.objects.update_or_create(
                        user=user, # Link the identity
                        defaults={
                            'full_name': real_name,
                            'email': f"agent_{ext_num}@local.pbx",
                            'is_active': True
                        }
                    )

                    # 3. Clean up other agents holding this extension number
                    Extension.objects.filter(extension_number=ext_num).exclude(agent=agent).delete()

                    # 4. Assign the Extension to the Agent
                    Extension.objects.update_or_create(
                        agent=agent,
                        defaults={
                            'extension_number': ext_num,
                            'is_active': True,
                            'technology': 'SIP'
                        }
                    )

            self.stdout.write(self.style.SUCCESS(f'Successfully synced {len(rows)} extensions.'))
        finally:
            connection.close()