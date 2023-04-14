# Продуктовый помощник
![main_workflow](https://github.com/Petro2561/foodgram-project-react/actions/workflows/main.yml/badge.svg)
http://51.250.75.102/
login: admin
passwird: pete3015

Foodgram - продуктовый помощник с базой кулинарных рецептов. На этом сервисе пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

## Tecnhologies:
- Python 3.10
- Django 3.2.16
- Django REST framework 3.14
- Nginx
- Docker
- Postgres

## Развернуть проект на удаленном сервере:
Клонировать репозиторий:
https://github.com/petro2561/oodgram-project-react.git
Установить на сервере Docker, Docker Compose:
```sudo apt install curl                                   # установка утилиты для скачивания файлов
curl -fsSL https://get.docker.com -o get-docker.sh      # скачать скрипт для установки
sh get-docker.sh                                        # запуск скрипта
sudo apt-get install docker-compose-plugin              # последняя версия docker compose
```
Скопировать на сервер файлы docker-compose.yml, nginx.conf из папки infra (команды выполнять находясь в папке infra):
```
scp docker-compose.yml nginx.conf username@IP:/home/username/   # username - имя пользователя на сервере
                                                                # IP - публичный IP сервера
```

Создать и запустить контейнеры Docker, выполнить команду на сервере (версии команд "docker compose" или "docker-compose" отличаются в зависимости от установленной версии Docker Compose):
```
sudo docker compose up -d
После успешной сборки выполнить миграции:
sudo docker compose exec backend python manage.py migrate
Создать суперпользователя:
sudo docker compose exec backend python manage.py createsuperuser
Собрать статику:
sudo docker compose exec backend python manage.py collectstatic --noinput
Наполнить базу данных содержимым из файла ingredients.json:
sudo docker compose exec backend python manage.py loaddata ingredients.json
```

Автор backend'а:
Петр Анреев (c) 2022