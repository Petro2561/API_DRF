from rest_framework import permissions


class AuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение на изменение только для служебного персонала и автора.
    Остальным только чтение объекта.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or (request.user == obj.author)
            or request.user.is_staff
        )
