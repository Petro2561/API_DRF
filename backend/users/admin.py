from django.contrib import admin

from .models import CustomUser, Subscribe


@admin.register(CustomUser)
class AdminCustomUser(admin.ModelAdmin):
    list_display = ('username', 'id', 'first_name', 'last_name')
    fields = (
        ('username', 'email', ),
        ('first_name', 'last_name', 'subscribers')
    )
    search_fields = ('username', 'email',)
# подписками можно управлять внутри пользователя

admin.site.register(Subscribe)