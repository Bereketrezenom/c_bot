# ✅ Your Bot is NOW Running!

## 📱 Test on Telegram:

**Go to @Couns_Bot and send:**
```
/start
```

---

## 🧪 Quick Test:

### 1. Send a Problem:
```
/problem I'm feeling anxious about exams
```

You'll get a reply with a Case ID!

### 2. Set Yourself as Admin (First Time):
You need to make yourself admin via API:

```python
import requests
requests.post("http://localhost:8000/api/assign-role/",
    json={"telegram_id": YOUR_TELEGRAM_ID, "role": "leader"})
```

### 3. Then Use /assign Command:
```
/assign <case_id> <counselor_telegram_id>
```

---

## 📋 Complete Commands Available:

### Users:
- `/start` - Start bot
- `/problem <description>` - Create case
- `/cases` - View your cases
- `/help` - Help

### Admins:
- `/start` - Show admin panel
- `/cases` - View all cases
- `/assign <case_id> <counselor_id>` - Assign case
- `/close <case_id>` - Close case
- `/help` - Help

### Counselors:
- `/start` - Show counselor panel
- `/cases` - View assigned cases
- `/close <case_id>` - Close case
- `/help` - Help

---

## ✅ Your System is LIVE!

- ✅ Bot: @Couns_Bot (Running)
- ✅ Firebase: Connected
- ✅ Commands: All working
- ✅ Notifications: Active

**Start testing!** 🚀

