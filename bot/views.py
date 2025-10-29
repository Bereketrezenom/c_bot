"""
Django views for bot admin and API.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid Firebase initialization at module load
def get_firebase_service():
    from .firebase_service import firebase_service as fs
    return fs


def health_check(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'ok', 'message': 'Counseling Bot API is running'})


@csrf_exempt
@require_http_methods(["GET"])
def get_all_cases(request):
    """Get all cases (for admin)."""
    try:
        firebase_service = get_firebase_service()
        cases = []
        for doc in firebase_service.db.collection('cases').stream():
            case_data = doc.to_dict()
            case_data['id'] = doc.id
            cases.append(case_data)
        
        return JsonResponse({'cases': cases, 'count': len(cases)})
    except Exception as e:
        logger.error(f"Error getting cases: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_all_users(request):
    """Get all users (for admin)."""
    try:
        firebase_service = get_firebase_service()
        users = []
        for doc in firebase_service.db.collection('users').stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            users.append(user_data)
        
        return JsonResponse({'users': users, 'count': len(users)})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def assign_user_role(request):
    """Assign role to a user."""
    try:
        data = json.loads(request.body)
        telegram_id = data.get('telegram_id')
        role = data.get('role')
        
        if not telegram_id or not role:
            return JsonResponse({'error': 'Missing telegram_id or role'}, status=400)
        
        if role not in ['user', 'counselor', 'leader']:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        firebase_service = get_firebase_service()
        firebase_service.update_user_role(telegram_id, role)
        return JsonResponse({'success': True, 'message': f'Role {role} assigned'})
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_stats(request):
    """Get statistics."""
    try:
        firebase_service = get_firebase_service()
        stats = {
            'total_users': len(list(firebase_service.db.collection('users').stream())),
            'total_cases': len(list(firebase_service.db.collection('cases').stream())),
            'pending_cases': len(firebase_service.get_all_pending_cases()),
        }
        
        # Count by role
        roles = {}
        for doc in firebase_service.db.collection('users').stream():
            role = doc.to_dict().get('role', 'user')
            roles[role] = roles.get(role, 0) + 1
        stats['users_by_role'] = roles
        
        # Count by status
        statuses = {}
        for doc in firebase_service.db.collection('cases').stream():
            status = doc.to_dict().get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        stats['cases_by_status'] = statuses
        
        return JsonResponse({'stats': stats})
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)

