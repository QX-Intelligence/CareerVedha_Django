from rest_framework.exceptions import PermissionDenied

# Role levels (higher = more power)
ROLE_LEVELS = {
    "CONTRIBUTOR": 1,
    "EDITOR": 2,
    "PUBLISHER": 3,
    "ADMIN": 4,
    "SUPER_ADMIN": 5,
}


def _normalize_role(role: str) -> str:
    if not role:
        return ""
    return role.replace("ROLE_", "").strip().upper()


def get_role_level(role: str) -> int:
    """
    Returns numeric privilege level for a role.
    Unknown role -> 0
    """
    role = _normalize_role(role)
    return ROLE_LEVELS.get(role, 0)


# =====================================================
# STRICT ALLOW-LIST (your current style)
# =====================================================


# =====================================================
# HIERARCHY CHECK (BEST FOR CMS)
# =====================================================
def require_min_role(user: dict, min_role: str):
    """
    Hierarchy permission check.

    Example:
      require_min_role(user, "EDITOR")
        -> allows EDITOR, PUBLISHER, ADMIN, SUPER_ADMIN
    """
    user_role = _normalize_role(user.get("role"))
    user_level = get_role_level(user_role)

    min_level = get_role_level(min_role)

    if user_level < min_level:
        raise PermissionDenied("Insufficient permissions")


# =====================================================
# COMMON ROLE CONSTANTS (optional, for clean code)
# =====================================================
CREATE_ARTICLE_MIN_ROLE = "CONTRIBUTOR"
EDIT_ARTICLE_MIN_ROLE = "EDITOR"
PUBLISH_ARTICLE_MIN_ROLE = "PUBLISHER"
ADMIN_MIN_ROLE = "ADMIN"
from rest_framework.permissions import BasePermission

class IsAuthenticatedDict(BasePermission):
    """
    Permission class for dictionary-based users (JWT).
    Works when request.user is a dict from JWTAuthentication.
    """
    def has_permission(self, request, view):
        return bool(request.user and isinstance(request.user, dict))

class HasMinRole(BasePermission):
    """
    DRF Permission class for hierarchy-based role checks.
    """
    def __init__(self, min_role):
        self.min_role = min_role

    def has_permission(self, request, view):
        if not request.user or not isinstance(request.user, dict):
            return False
            
        user_role = _normalize_role(request.user.get("role"))
        user_level = get_role_level(user_role)
        min_level = get_role_level(self.min_role)

        return user_level >= min_level

# Helper to create permission classes on the fly
def min_role_permission(role_name):
    class DynamicHasMinRole(HasMinRole):
        def __init__(self):
            super().__init__(role_name)
    return DynamicHasMinRole