# Telegram Counseling Bot

A Django-based Telegram bot for anonymous counseling services with Firebase Firestore integration.

## 🎯 Features

- **Anonymous Chat**: Users and counselors interact without revealing identities
- **Role-Based Access**: Three roles (User, Counselor, Counseling Leader)
- **Case Assignment**: Leaders assign cases to specific counselors
- **Chat Logging**: All conversations securely stored in Firestore
- **Real-time Notifications**: Telegram notifications for new cases and messages
- **Data Privacy**: User information and messages are anonymized and protected

## 🛠️ Technology Stack

- **Backend**: Django 4.2
- **Bot Framework**: python-telegram-bot
- **Database**: Firebase Firestore
- **Language**: Python 3.8+

## 📋 Prerequisites

1. Python 3.8 or higher
2. Firebase account and project
3. Telegram Bot Token from [@BotFather](https://t.me/botfather)

## 🚀 Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Enable Firestore Database
4. Download your service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save it as `serviceAccountKey.json` in the project root

### 3. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Firebase
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

### 5. Run Django Migrations

```bash
python manage.py migrate
```

### 6. Create a Superuser (Optional, for Admin Dashboard)

```bash
python manage.py createsuperuser
```

### 7. Run the Bot

```bash
python manage.py run_bot
```

Or run Django and bot separately:

```bash
# Terminal 1 - Django server
python manage.py runserver

# Terminal 2 - Bot
python manage.py run_bot
```

## 📱 Usage

### For Users

1. Start the bot on Telegram
2. Click "Send a Problem"
3. Type your message
4. Wait for assignment and counseling

### For Counseling Leaders

1. Leader role is assigned via API or admin
2. Receive notifications for new cases
3. Assign cases to counselors
4. Monitor case progress

### For Counselors

1. Counselor role is assigned via API or admin
2. Receive notifications when assigned to a case
3. Start anonymous conversation with users
4. Provide counseling support

## 🔧 API Endpoints

- `GET /api/health/` - Health check
- `GET /api/cases/` - Get all cases
- `GET /api/users/` - Get all users
- `GET /api/stats/` - Get statistics
- `POST /api/assign-role/` - Assign role to user
  ```json
  {
    "telegram_id": 123456789,
    "role": "counselor"
  }
  ```

## 🏗️ Project Structure

```
counseling_bot/
├── bot/                   # Main bot application
│   ├── firebase_service.py    # Firestore operations
│   ├── telegram_bot.py       # Bot handlers and logic
│   ├── views.py              # API views
│   └── management/
│       └── commands/
│           └── run_bot.py    # Bot runner command
├── counseling_bot/         # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── requirements.txt       # Python dependencies
├── manage.py             # Django management
└── README.md
```

## 📊 Workflow

1. User starts bot and sends a problem
2. Case is created in Firestore with "pending" status
3. Counseling Leader receives notification
4. Leader assigns case to a counselor
5. Counselor receives notification
6. Anonymous conversation begins
7. Messages are stored in real-time in Firestore
8. Case can be closed when finished

## 🔐 Role Management

Roles can be assigned via API:

```python
import requests

url = "http://localhost:8000/api/assign-role/"
data = {
    "telegram_id": 123456789,
    "role": "counselor"  # or "leader"
}
response = requests.post(url, json=data)
```

## 📦 Deployment

### Using Render (Recommended)

1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables in Render dashboard
4. Deploy both Django service and bot worker

### Environment Variables for Production

```env
DJANGO_SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
TELEGRAM_BOT_TOKEN=your-bot-token
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

## 🐛 Troubleshooting

### Bot not responding
- Check if bot token is correct
- Verify bot is running (`python manage.py run_bot`)
- Check bot logs for errors

### Firebase connection issues
- Ensure `serviceAccountKey.json` exists
- Check Firebase credentials path
- Verify Firestore is enabled in Firebase console

### Permission errors
- Make sure file permissions are correct
- Check environment variables are set

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📧 Support

For support, please open an issue on GitHub or contact the development team.

