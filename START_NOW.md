# ✅ START YOUR BOT NOW!

## 🚀 Quick Start (2 Commands):

### Terminal 1 - Start Bot:
```bash
venv\Scripts\activate
python manage.py run_bot
```

### Terminal 2 - Start Django (Optional, for admin panel):
```bash
venv\Scripts\activate
python manage.py runserver
```

---

## 📱 Test Your Bot on Telegram:

### 1. Open Telegram
Search for: **@Couns_Bot**

### 2. Send `/start`
You'll see a welcome message.

### 3. Create a Test Case:
Send: `/problem I need help with stress management`

### 4. Check as Admin:
The admin (you) will get a notification!

---

## 🎯 How the System Works:

### Step 1: User Creates Case
```
User: /problem I have anxiety
Bot: ✅ Case submitted! Case ID: xyz789
```

### Step 2: Admin Sees Notification
```
Bot → Admin: 🆕 New Case
            Case ID: xyz789
            Problem: I have anxiety
            Use /assign xyz789 <counselor_id>
```

### Step 3: Admin Assigns
```
Admin: /assign xyz789 123456789
Bot: ✅ Case assigned!
```

### Step 4: Counselor Gets Notification
```
Bot → Counselor: 📋 Case Assigned!
                 Case: xyz789 - I have anxiety
```

### Step 5: Anonymous Chat
```
User: Hello!
Bot → Counselor: 💬 Anonymous User (xyz789)
                    Hello!
```

---

## 🔑 Set Yourself as Admin:

After starting bot and Django, use the API:

```bash
curl -X POST http://localhost:8000/api/assign-role/ ^
  -H "Content-Type: application/json" ^
  -d "{\"telegram_id\": YOUR_TELEGRAM_ID, \"role\": \"leader\"}"
```

OR in Python:
```python
import requests
requests.post("http://localhost:8000/api/assign-role/", 
    json={"telegram_id": YOUR_ID, "role": "leader"})
```

---

## 📋 Summary:

✅ Bot: @Couns_Bot on Telegram  
✅ All communication: Via Telegram  
✅ Cases: Stored in Firebase  
✅ Admin panel: Optional web dashboard  
✅ Role management: Via API  

**Ready to use!** 🎉

