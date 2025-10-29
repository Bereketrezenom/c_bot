# 🚨 IMPORTANT: How to Start Correctly

## The Problem:
You're running the server with system Python, not the virtual environment.
That's why Firebase can't be found!

## The Solution - Follow These Steps EXACTLY:

### Step 1: Close Current Server
Press `CTRL+C` in the terminal where the server is running.

### Step 2: Open a NEW terminal
Or use the same one after stopping.

### Step 3: Go to project folder
```bash
cd C:\Users\NEZHAB\Desktop\Counseling_bot
```

### Step 4: ACTIVATE the virtual environment FIRST!
```bash
venv\Scripts\activate
```

You should see `(venv)` at the start of your prompt.

### Step 5: Start the server
```bash
python manage.py runserver
```

### Step 6: Open your dashboard
Go to: http://localhost:8000/admin-ui/

---

## Quick One-Line Start:

```bash
cd C:\Users\NEZHAB\Desktop\Counseling_bot && venv\Scripts\activate && python manage.py runserver
```

---

## Why This Happens:
- Windows can use multiple Python installations
- Your venv has firebase-admin installed
- But system Python doesn't
- Always activate venv FIRST!

---

## Verification:
After starting, you should see:
```
Starting development server at http://127.0.0.1:8000/
```

And when you visit the admin-ui, you should NOT see "Firebase not connected" errors.

