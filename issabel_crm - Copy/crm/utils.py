def normalize_phone_number(phone):
    if not phone:
        return ''

    phone = str(phone).strip().replace(' ', '').replace('-', '')

    if phone.startswith('+'):
        phone = phone[1:]

    if phone.startswith('0098'):
        phone = '0' + phone[4:]
    elif phone.startswith('98'):
        phone = '0' + phone[2:]

    return phone
