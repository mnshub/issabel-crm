import pymysql
import pymysql.err
from config import settings
from zoneinfo import ZoneInfo
from django.utils import timezone
from crm.models import CallLog, Customer
from crm.utils import normalize_phone_number
from django.core.management.base import BaseCommand
from datetime import datetime, date, timezone as dt_timezone

class Command(BaseCommand):
    help = "Import CDR records from Issabel/Asterisk database"

    def handle(self, *args, **kwargs):
        imported = 0
        skipped = 0
        

        pbx_tz = ZoneInfo('Asia/Tehran')

        try:
            connection = pymysql.connect(
                host=settings.PBX_DB_HOST,
                user=settings.PBX_DB_USER,
                password=settings.PBX_DB_PASS,
                database='asteriskcdrdb', 
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.err.OperationalError as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to Issabel database: {e}"))
            return

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT *
                    FROM cdr
                    ORDER BY calldate DESC
                    LIMIT 2000
                """)
                rows = cursor.fetchall()

                for row in rows:
                    uniqueid = row.get('uniqueid')
                    if not uniqueid or CallLog.objects.filter(uniqueid=uniqueid).exists():
                        skipped += 1
                        continue

                    src = normalize_phone_number(row.get('src', ''))
                    dst = normalize_phone_number(row.get('dst', ''))

                    customer = Customer.objects.filter(phone_number=src).first() or \
                               Customer.objects.filter(phone_number=dst).first()

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

                    # --- TIMEZONE FIX START ---
                    call_time = row.get('calldate')
                    if call_time:
                        # If naive, localize as Tehran time, then convert to UTC for DB
                        if timezone.is_naive(call_time):
                            call_time = call_time.replace(tzinfo=pbx_tz)
                        call_time = call_time.astimezone(dt_timezone.utc)
                    # --- TIMEZONE FIX END ---

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
            self.stdout.write(self.style.ERROR(f"An error occurred during data processing: {e}"))
        finally:
            connection.close()

        self.stdout.write(self.style.SUCCESS(f"Import complete. Imported: {imported}, Skipped: {skipped}"))