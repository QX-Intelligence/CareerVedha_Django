from rest_framework import authentication
from .jwt import get_user_from_jwt

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            user_data = get_user_from_jwt(request)
            # DRF expects a (user, auth) tuple. 
            # We don't have a real User object since it's cross-service, 
            # so we'll pass the dict as the 'user'.
            return (user_data, None)
        except Exception:
            return None
