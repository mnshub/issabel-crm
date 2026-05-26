# Issabel-CRM Integration System

A real-time, WebSocket-enabled Customer Relationship Management (CRM) system built with Django, designed to natively integrate with Issabel PBX (Asterisk). 

## 🌟 Core Features (Current)
* **Real-Time Call Popups:** Uses Asterisk Manager Interface (AMI) and Django Channels to push live incoming call notifications to the specific agent's browser.
* **Click-to-Dial:** Agents can initiate calls directly from the CRM dashboard, triggering their desk phone to dial automatically.
* **Call Log Synchronization:** Automatically imports and structures Call Detail Records (CDRs) and call recordings from the Issabel MySQL database.
* **Smart Dashboard:** Filters call history, excluding internal agent-to-agent misdials, and separates inbound vs. outbound logs.

## 🛠️ Technology Stack
* **Backend:** Python, Django 4.x, Django Channels (WebSockets)
* **VoIP Integration:** Panoramisk (Async AMI library), Asterisk/Issabel PBX
* **Frontend:** HTML5, CSS3, Vanilla JavaScript
* **Database:** SQLite (Django), MySQL (Issabel CDR)

## 🚀 Setup & Installation
1. **Clone the repository.**
2. **Create a virtual environment:** `python -m venv venv`
3. **Activate environment & install dependencies:** `pip install -r requirements.txt`
4. **Configure Settings:** Update `config/settings.py` with your Issabel IP and AMI credentials.
5. **Run Migrations:** `python manage.py migrate`
6. **Start the ASGI Server (Daphne/Uvicorn):** `python manage.py runserver`
7. **Start the AMI Listener (in a separate terminal):** `python crm/ami_listener.py`

## 🔒 Requirements on Issabel PBX
* You must configure an AMI user in `/etc/asterisk/manager.conf` with `read` and `write` permissions including `originate`.
* Recordings folder `/var/spool/asterisk/monitor/` must be accessible (e.g., via Samba share) for browser playback.