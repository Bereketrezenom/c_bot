# Admin Setup Guide

## How to Set Up and Use the Admin Interface

### 1. Create a Superuser (Admin Account)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin username, email, and password.

### 2. Access the Admin Interface

1. Start the Django server:
   ```bash
   python manage.py runserver
   ```

2. Open your browser and go to:
   ```
   http://localhost:8000/admin/
   ```

3. Log in with your superuser credentials

### 3. Access the Counseling Cases Dashboard

After logging in, go to:
```
http://localhost:8000/admin/counseling/
```

This is your **main dashboard** for managing cases!

### 4. How It Works

#### When a user sends a problem in Telegram:

1. **User chats with bot**: "Hi" or sends a problem
2. **Case is created** in Firebase Firestore
3. **Admin receives notification** (if leader/counselor is assigned in Firebase)
4. **Admin sees the case** in the dashboard at `/admin/counseling/`

#### Admin assigns a counselor:

1. Click on "Assign Case" button on any pending case
2. Select a counselor from the dropdown
3. Click "Assign Case"
4. Counselor receives notification in Telegram
5. Counselor can now chat with the user

### 5. Assigning User Roles

To make users counselors or leaders, use the API:

```bash
# Make someone a leader (can assign cases)
curl -X POST http://localhost:8000/api/assign-role/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_TELEGRAM_ID, "role": "leader"}'

# Make someone a counselor
curl -X POST http://localhost:8000/api/assign-role/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": COUNSELOR_TELEGRAM_ID, "role": "counselor"}'
```

Or use Python:
```python
import requests

url = "http://localhost:8000/api/assign-role/"
data = {
    "telegram_id": 123456789,  # Telegram user ID
    "role": "counselor"  # or "leader" or "user"
}
response = requests.post(url, json=data)
print(response.json())
```

### 6. Dashboard Features

The dashboard shows:
- ✅ All cases with status (pending, assigned, active, closed)
- ✅ User information (name, username)
- ✅ Counselor information (if assigned)
- ✅ Problem description
- ✅ Message count
- ✅ Assignment controls

### 7. Testing the Flow

1. Start both servers:
   ```bash
   # Terminal 1: Django
   python manage.py runserver
   
   # Terminal 2: Bot
   python manage.py run_bot
   ```

2. Open Telegram and message @Couns_Bot
3. Send "/start"
4. Click "Send a Problem"
5. Type your problem
6. Go to http://localhost:8000/admin/counseling/
7. See your case appear!
8. Assign it to a counselor

### 8. Admin Notifications

Currently, admins/leaders need to:
1. Check the dashboard manually OR
2. Get notified via Telegram (if their role is set as "leader" in Firebase)

To enable Telegram notifications for leaders, set their role in Firebase to "leader".

### 9. Making Yourself a Leader

1. Get your Telegram ID from a bot like @userinfobot
2. Assign role via API:
```bash
curl -X POST http://localhost:8000/api/assign-role/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_TELEGRAM_ID, "role": "leader"}'
```

3. Or manually update in Firebase:
   - Go to Firestore console
   - Find your user document
   - Change "role" field to "leader"

## Quick Reference

| URL | Purpose |
|-----|---------|
| /admin/ | Django admin login |
| /admin/counseling/ | **Cases dashboard (MAIN)** |
| /admin/bot/cases/api/ | Cases API |
| /admin/bot/users/api/ | Users API |
| /api/health/ | Health check |
| /api/stats/ | Statistics |

## Troubleshooting

**Can't access admin?**
- Make sure you created a superuser
- Check you're logged in at /admin/

**Dashboard shows "Loading..." forever?**
- Check if Django server is running
- Check browser console for errors
- Make sure Firebase is initialized

**No cases showing?**
- Test by sending a message to the bot
- Check Firebase Firestore for data
- Verify serviceAccountKey.json exists

**Can't assign cases?**
- Make sure you're logged in
- Check browser console for errors
- Verify counselors exist in Firebase

## Next Steps

1. ✅ Create superuser
2. ✅ Access dashboard
3. ✅ Make yourself a leader
4. ✅ Assign counselors to cases
5. 🎉 Start managing cases!

