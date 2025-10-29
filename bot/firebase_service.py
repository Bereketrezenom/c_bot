"""
Firebase Firestore service for managing database operations.
"""
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError as e:
    print(f"Warning: firebase_admin not installed. {e}")
    firebase_admin = None
    firestore = None

from django.conf import settings
from datetime import datetime
from pathlib import Path
import os


class FirebaseService:
    def __init__(self):
        if firebase_admin is None:
            raise ImportError("firebase-admin is not installed. Run: pip install firebase-admin")
        
        if not firebase_admin._apps:
            cred_path_setting = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
            cred_path = Path(cred_path_setting)
            if not cred_path.is_absolute():
                base_dir = Path(getattr(settings, 'BASE_DIR', '.'))
                cred_path = base_dir / cred_path
            print(f"[Firebase] Using credentials path: {cred_path}")
            try:
                if cred_path.exists():
                    cred = credentials.Certificate(str(cred_path))
                    firebase_admin.initialize_app(cred)
                    print("[Firebase] Initialized with service account credentials")
                else:
                    print(f"[Firebase] Credentials file not found at {cred_path}. Trying default app init...")
                    firebase_admin.initialize_app()
                    print("[Firebase] Initialized default app (no explicit credentials)")
            except Exception as e:
                print(f"[Firebase] Error initializing Firebase: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        try:
            self.db = firestore.client()
            print("[Firebase] Firestore client created successfully")
        except Exception as e:
            print(f"[Firebase] Error creating Firestore client: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def create_user(self, user_data):
        """Create a new user in Firestore."""
        user_ref = self.db.collection('users').document(str(user_data['telegram_id']))
        user_ref.set({
            'telegram_id': user_data['telegram_id'],
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'role': user_data.get('role', 'user'),  # user, counselor, leader
            'active_cases': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        return user_ref
    
    def get_user(self, telegram_id):
        """Get user from Firestore."""
        user_ref = self.db.collection('users').document(str(telegram_id))
        doc = user_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    def update_user_role(self, telegram_id, new_role):
        """Update user's role."""
        user_ref = self.db.collection('users').document(str(telegram_id))
        user_ref.update({
            'role': new_role,
            'updated_at': datetime.now().isoformat()
        })
    
    def create_case(self, case_data):
        """Create a new counseling case."""
        case_ref = self.db.collection('cases')
        new_case = {
            'user_telegram_id': case_data['user_telegram_id'],
            'problem': case_data['problem'],
            'status': 'pending',  # pending, assigned, active, closed
            'assigned_counselor_id': None,
            'counseling_leader_id': None,
            'messages': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        doc_ref = case_ref.add(new_case)[1]
        return doc_ref.id
    
    def get_case(self, case_id):
        """Get case from Firestore."""
        case_ref = self.db.collection('cases').document(case_id)
        doc = case_ref.get()
        if doc.exists:
            return {**doc.to_dict(), 'id': doc.id}
        return None
    
    def assign_case(self, case_id, counselor_id, leader_id):
        """Assign case to a counselor."""
        case_ref = self.db.collection('cases').document(case_id)
        case_ref.update({
            'status': 'assigned',
            'assigned_counselor_id': counselor_id,
            'counseling_leader_id': leader_id,
            'updated_at': datetime.now().isoformat()
        })
    
    def add_message_to_case(self, case_id, message_data):
        """Add a message to a case's chat."""
        case_ref = self.db.collection('cases').document(case_id)
        case_doc = case_ref.get()
        
        if case_doc.exists:
            case_data = case_doc.to_dict()
            messages = case_data.get('messages', [])
            messages.append({
                'sender_role': message_data['sender_role'],
                'sender_telegram_id': message_data['sender_telegram_id'],
                'message': message_data['message'],
                'timestamp': datetime.now().isoformat()
            })
            case_ref.update({
                'messages': messages,
                'status': 'active',
                'updated_at': datetime.now().isoformat()
            })
    
    def close_case(self, case_id):
        """Close a counseling case."""
        case_ref = self.db.collection('cases').document(case_id)
        case_ref.update({
            'status': 'closed',
            'updated_at': datetime.now().isoformat()
        })
    
    def get_all_pending_cases(self):
        """Get all pending cases."""
        cases_ref = self.db.collection('cases').where('status', '==', 'pending')
        docs = cases_ref.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_user_cases(self, telegram_id):
        """Get all cases for a user."""
        cases_ref = self.db.collection('cases').where('user_telegram_id', '==', telegram_id)
        docs = cases_ref.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_counselor_cases(self, counselor_id):
        """Get all cases assigned to a counselor."""
        cases_ref = self.db.collection('cases').where('assigned_counselor_id', '==', counselor_id)
        docs = cases_ref.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_all_users_by_role(self, role):
        """Get all users with a specific role."""
        users_ref = self.db.collection('users').where('role', '==', role)
        docs = users_ref.stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]


# Lazy singleton - will be created on first access
_firebase_service_instance = None

def get_firebase_service():
    global _firebase_service_instance
    if _firebase_service_instance is None:
        try:
            _firebase_service_instance = FirebaseService()
            print("Firebase service initialized successfully!")
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")
            import traceback
            traceback.print_exc()
            return None
    return _firebase_service_instance

# For backward compatibility
firebase_service = None

