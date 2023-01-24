from django.contrib import admin

from .models import CustomUser


@admin.register(CustomUser)
class AdminCustomUser(admin.ModelAdmin):
    list_display = ('username',)
    list_filter = ('username', 'email',)



