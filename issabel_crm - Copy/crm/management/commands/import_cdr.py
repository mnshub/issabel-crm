import pymysql
from django.core.management.base import BaseCommand
from crm.models import CallLog, Customer
from crm.utils import normalize_phone_number
from datetime import datetime, date
from django.utils import timezone



class Command(BaseCommand):
    help = "Import CDR records from Issabel/Asterisk database"

    def handle(self, *args, **kwargs):
        connection = pymysql.connect(
            host='10.28.0.115',
            user='crm_reader',
            password='Admin1234',
            database='asteriskcdrdb',
            cursorclass=pymysql.cursors.DictCursor
        )

        imported = 0
        skipped = 0

        try:
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

        finally:
            connection.close()

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. Imported: {imported}, Skipped: {skipped}"
            )
        )
