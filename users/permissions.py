from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение на чтение для всех, изменение только для владельца
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user


class IsAdminOrOwner(permissions.BasePermission):
    """
    Разрешение для администратора или владельца
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user
