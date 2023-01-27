from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=254,
        verbose_name='Почта',
        unique=True,
        error_messages={
            "unique": "Пользователь с такой почтой уже существует",
        },
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия'
    )
    subscribers = models.ManyToManyField(
        'self',
        symmetrical=False,
        verbose_name='Подписчики',
        related_name='subscribed',
        blank=True
    )
    username = models.CharField(
        "Имя пользователя",
        max_length=150,
        unique=True,
        help_text=(
            "Введите уникальное имя пользователя. Максимум 150 символов. "
            "Используйте только английские буквы, цифры и символы @/./+/-/_"
        ),
        error_messages={
            "unique": "Пользователь с таким именем уже существует",
        },
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
