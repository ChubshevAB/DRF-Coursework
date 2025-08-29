from rest_framework import permissions


class IsOwnerOrPublicReadOnly(permissions.BasePermission):
    """
    Разрешение на чтение публичных привычек и полный доступ к своим
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.user == request.user
        return obj.user == request.user
