# 🚀 How to Use Your Telegram Counseling Bot

## ✅ System is Ready!

### Start the Bot:

```bash
# Activate venv
venv\Scripts\activate

# Run bot
python manage.py run_bot
```

---

## 📱 Telegram Commands

### For Users (Regular People):

| Command | What It Does |
|---------|--------------|
| `/start` | Start the bot |
| `/problem <your issue>` | Create a counseling request |
| `/cases` | View your cases |
| `/help` | Show help |

**Example:**
```
/problem I'm feeling stressed about my upcoming exams and need someone to talk to
```

---

### For Admins/Leaders:

| Command | What It Does |
|---------|--------------|
| `/start` | Show admin panel |
| `/cases` | View all pending cases |
| `/assign <case_id> <counselor_telegram_id>` | Assign case to counselor |
| `/close <case_id>` | Close a case |
| `/help` | Show help |

**Example:**
```
/assign abc123def 123456789
```

---

### For Counselors:

| Command | What It Does |
|---------|--------------|
| `/start` | Show counselor panel |
| `/cases` | View your assigned cases |
| `/close <case_id>` | Close a case |
| `/help` | Show help |

---

## 🔄 Complete Workflow:

### 1. User Creates Case:
```
User: /problem I need help with anxiety
Bot: ✅ Your case has been submitted!
     Case ID: abc123def
     A counselor will be assigned soon.
```

### 2. Admin Gets Notification:
```
Bot → Admin: 🆕 New Counseling Case
            Case ID: abc123def
            Problem: I need help with anxiety
            
            Use /assign abc123def <counselor_id> to assign
```

### 3. Admin Assigns:
```
Admin: /assign abc123def 123456789
Bot: ✅ Case assigned successfully!
```

### 4. Counselor Gets Notification:
```
Bot → Counselor: 📋 New Case Assigned!
                 Case ID: abc123def
                 Problem: I need help with anxiety
                 
                 Use /reply abc123def to start
```

### 5. Anonymous Chat:
```
User → Bot → Counselor: 💬 Anonymous User (Case abc123def)
                    I'm having trouble sleeping

Counselor → Bot → User: 💬 Your Counselor
                          I understand. Let's talk about that.
```

---

## 🎯 Setup Admin/Counselor Roles:

### Make Someone an Admin:
```python
import requests

# Make yourself admin
response = requests.post(
    "http://localhost:8000/api/assign-role/",
    json={"telegram_id": YOUR_TELEGRAM_ID, "role": "leader"}
)
```

### Make Someone a Counselor:
```python
response = requests.post(
    "http://localhost:8000/api/assign-role/",
    json={"telegram_id": COUNSELOR_TELEGRAM_ID, "role": "counselor"}
)
```

---

## 🔑 Get Your Telegram ID:

Message @userinfobot on Telegram and it will tell you your ID.

---

## 🎉 That's It!

Your bot is at: **@Couns_Bot**

All communication happens through Telegram! No web interface needed!

