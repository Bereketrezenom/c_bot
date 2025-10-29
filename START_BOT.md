# How to Start Your Bot

## Quick Start (3 Steps)

### Step 1: Activate Virtual Environment
```bash
venv\Scripts\activate
```

### Step 2: Start Django Server
```bash
python manage.py runserver
```

### Step 3: Start Telegram Bot (in new terminal)
```bash
python manage.py run_bot
```

## Access Points

- **Admin Login**: http://localhost:8000/admin/
  - Username: `admin`
  - Password: `admin123`

- **Cases Dashboard**: http://localhost:8000/admin/counseling/

- **Bot on Telegram**: @Couns_Bot

## Complete Commands

Open Terminal 1:
```bash
cd C:\Users\NEZHAB\Desktop\Counseling_bot
venv\Scripts\activate
python manage.py runserver
```

Open Terminal 2:
```bash
cd C:\Users\NEZHAB\Desktop\Counseling_bot
venv\Scripts\activate
python manage.py run_bot
```

## That's It!

1. Login at http://localhost:8000/admin/
2. Go to dashboard at http://localhost:8000/admin/counseling/
3. Test the bot by messaging @Couns_Bot on Telegram
4. See cases appear in dashboard
5. Assign counselors to cases

