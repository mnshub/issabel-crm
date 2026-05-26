import pymysql
import pymysql.err
from django.core.management.base import BaseCommand
from crm.models import CallLog, Customer
from crm.utils import normalize_phone_number
from datetime import datetime, date
from django.utils import timezone

class Command(BaseCommand):
    help = "Import CDR records from Issabel/Asterisk database"

    def handle(self, *args, **kwargs):
        imported = 0
        skipped = 0

        # 1. Attempt to connect to the database. Catch network/auth errors first.
        try:
            connection = pymysql.connect(
                host='10.28.0.115',
                user='crm_reader',
                password='Admin1234',
                database='asteriskcdrdb',
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.err.OperationalError as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to Issabel database: {e}"))
            return # Exit the script safely if we can't connect

        # 2. Wrap the execution in a try...finally block
        try:
            # 3. The 'with' statement acts as a context manager for the cursor.
            # It guarantees that cursor.close() is called automatically when the block ends.
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT *
                    FROM cdr
                    ORDER BY calldate DESC
                    LIMIT 100
                """)
                rows = cursor.fetchall()

                for row in rows:
                    uniqueid = row.get('uniqueid')
                    if not uniqueid:
                        skipped += 1
                        continue

                    if CallLog.objects.filter(uniqueid=uniqueid).exists():
                        skipped += 1
                        continue

                    src = normalize_phone_number(row.get('src', ''))
                    dst = normalize_phone_number(row.get('dst', ''))

                    customer = Customer.objects.filter(phone_number=src).first()
                    if not customer:
                        customer = Customer.objects.filter(phone_number=dst).first()

                    # simple call type detection
                    if src.startswith('0') and not dst.startswith('0'):
                        call_type = 'incoming'
                        phone_number = src
                    elif not src.startswith('0') and dst.startswith('0'):
                        call_type = 'outbound'
                        phone_number = dst
                    else:
                        call_type = 'internal'
                        phone_number = src or dst

                    safe_row = {}

                    for key, value in row.items():
                        if isinstance(value, (datetime, date)):
                            safe_row[key] = value.isoformat()
                        else:
                            safe_row[key] = value

                    call_time = row.get('calldate')
                    if call_time and timezone.is_naive(call_time):
                        call_time = timezone.make_aware(call_time, timezone.get_current_timezone())

                    CallLog.objects.create(
                        customer=customer,
                        call_type=call_type,
                        phone_number=phone_number,
                        source_number=src,
                        destination_number=dst,
                        duration=row.get('duration') or 0,
                        billsec=row.get('billsec') or 0,
                        call_time=call_time,
                        disposition=(row.get('disposition') or 'UNKNOWN').upper(),
                        uniqueid=uniqueid,
                        linkedid=row.get('linkedid'),
                        raw_data=safe_row
                    )

                    imported += 1

        except Exception as e:
            # If ANY error happens during the loop (e.g., bad data format), catch it here
            self.stdout.write(self.style.ERROR(f"An error occurred during data processing: {e}"))
            
        finally:
            # 4. The 'finally' block executes NO MATTER WHAT (success or crash).
            # This guarantees the connection to Issabel is closed safely.
            connection.close()

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. Imported: {imported}, Skipped: {skipped}"
            )
        )