# Quick Start Guide

Your Counseling Bot is ready to run! 🚀

## 🎯 What You Have

✅ Django backend with API endpoints  
✅ Telegram bot integration  
✅ Firebase Firestore database  
✅ Admin dashboard  
✅ Role-based access system  

## 🚀 Running the Bot

### Option 1: Run Bot Only (Recommended)
```bash
python manage.py run_bot
```

### Option 2: Run Django + Bot Together
```bash
python run.py
```

### Option 3: Separate Terminals
```bash
# Terminal 1 - Django API
python manage.py runserver

# Terminal 2 - Bot
python manage.py run_bot
```

## 📱 Testing the Bot

1. Open Telegram
2. Search for **@Couns_Bot**
3. Send `/start` command
4. Follow the menu options

## 🔑 Your Bot Details

- **Username**: @Couns_Bot
- **Token**: Already configured in `.env`
- **Firebase**: Connected to `counseling-bot` project

## 🎮 Bot Features

### For Regular Users:
- Click "📝 Send a Problem"
- Describe your issue
- Wait for counselor assignment
- Chat anonymously

### For Leaders:
Assign role via API:
```bash
curl -X POST http://localhost:8000/api/assign-role/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_TELEGRAM_ID, "role": "leader"}'
```

### For Counselors:
Assign role via API:
```bash
curl -X POST http://localhost:8000/api/assign-role/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": COUNSELOR_TELEGRAM_ID, "role": "counselor"}'
```

## 🌐 API Endpoints

- `http://localhost:8000/api/health/` - Health check
- `http://localhost:8000/api/stats/` - Get statistics
- `http://localhost:8000/api/cases/` - View all cases
- `http://localhost:8000/api/users/` - View all users

## 🐛 Troubleshooting

**Bot not responding?**
- Check if bot is running: `python manage.py run_bot`
- Verify token in `.env` file
- Check logs for errors

**Firebase errors?**
- Verify `serviceAccountKey.json` exists
- Check Firestore is enabled in Firebase console

**Import errors?**
- Activate virtual environment: `venv\Scripts\activate` (Windows)
- Install dependencies: `pip install -r requirements.txt`

## 📊 Next Steps

1. Test the bot with `/start`
2. Create a test case
3. Assign roles to Telegram users
4. Deploy to production (Render/Heroku)

## 🔗 Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Firebase Firestore](https://firebase.google.com/docs/firestore)
- [Django Documentation](https://docs.djangoproject.com/)

## 💡 Tips

- Keep `.env` file secure and don't commit it
- Firebase credentials are in `serviceAccountKey.json`
- Bot token and Firebase credentials are sensitive information
- Test locally before deploying

Happy counseling! 🎉

