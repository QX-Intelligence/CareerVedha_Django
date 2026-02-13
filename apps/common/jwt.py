import jwt
from django.conf import settings
from rest_framework.exceptions import PermissionDenied

def get_user_from_jwt(request):
    """
    Decodes JWT and caches the result in the request object to avoid redundant decoding.
    """
    if hasattr(request, "_cached_user_context"):
        return request._cached_user_context

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise PermissionDenied("JWT required")

    token = auth.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )

        # Normalize role
        role = None
        if "role" in payload:
            role = payload["role"]
        elif "roles" in payload and isinstance(payload["roles"], list) and payload["roles"]:
            role = payload["roles"][0]

        if not role:
            raise PermissionDenied("Role missing in token")

        user_ctx = {
            "user_id": payload.get("sub"),
            "role": role,
            "raw": payload,
        }
        request._cached_user_context = user_ctx
        return user_ctx

    except jwt.ExpiredSignatureError:
        raise PermissionDenied("JWT expired")
    except jwt.InvalidTokenError as e:
        raise PermissionDenied(f"Invalid JWT: {str(e)}")
