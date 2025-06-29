Сервис управления продажами и генерации аналитического отчета
Это Django-приложение, предназначенное для учета клиентов, заказов и продуктов, а также для генерации аналитических отчетов по продажам.

Описание проекта
Проект представляет собой RESTful API на базе Django и Django REST Framework, который позволяет управлять данными о продажах и формировать важные аналитические сводки в формате PDF. Для удобства работы с API интегрирована интерактивная документация Swagger UI.


REST API

Предоставляет следующие эндпоинты для взаимодействия с данными:

/api/products/

/api/customers/

/api/orders/

/api/orders/{id}/status/ (для обновления статуса заказа)

/api/reports/sales/?start=YYYY-MM-DD&end=YYYY-MM-DD (для генерации PDF-отчета)

СТЕК ТЕХНОЛОГИЙ

Python: 3.12+

Django: 5.2.3

Django REST Framework: 3.16.0

База данных: SQLite3 (для локальной разработки)

Генерация PDF: WeasyPrint

Шаблонизатор: Jinja2

Документация API: drf-yasg (Swagger UI)

УСТАНОВКА И ЗАПУСК ПРОЕКТА

Следуйте этим шагам для установки и запуска проекта на вашем локальном компьютере.

1. Клонирование репозитория
Bash

git clone <ваш_URL_репозитория_GitLab>
cd <название_вашего_проекта> # Например, cd Test

2. Создание и активация виртуального окружения
Настоятельно рекомендуется использовать виртуальное окружение для управления зависимостями.

Bash

python -m venv venv

ДЛЯ WINDOWS

.\venv\Scripts\activate

ДЛЯ MAC/LINUX

source venv/bin/activate

3. Установка зависимостей

Создайте файл requirements.txt в корне вашего проекта со следующим содержимым:

asgiref==3.8.1
Brotli==1.1.0
cffi==1.17.1
cssselect2==0.8.0
Django==5.2.3
django-filter==25.1
djangorestframework==3.16.0
drf-yasg==1.21.10
fonttools==4.58.4
inflection==0.5.1
Jinja2==3.1.6
MarkupSafe==3.0.2
packaging==25.0
pillow==11.2.1
pycparser==2.22
pydyf==0.11.0
pyphen==0.17.2
python-dotenv==1.1.0
pytz==2025.2
PyYAML==6.0.2
sqlparse==0.5.3
tinycss2==1.4.0
tinyhtml5==2.0.0
tzdata==2025.2
uritemplate==4.2.0
weasyprint==65.1
webencodings==0.5.1
zopfli==0.2.3.post1
Затем установите их:

Bash

pip install -r requirements.txt

4. Настройка базы данных и применение миграций

Проект использует SQLite3. Файл базы данных db.sqlite3 будет создан автоматически в корневой директории проекта при выполнении команды migrate. Вам не нужно создавать его вручную.

Bash

python manage.py makemigrations sales
python manage.py migrate

5. Запуск сервера разработки

Bash

python manage.py runserver

Теперь приложение должно быть доступно по адресу http://127.0.0.1:8000/.

ОПИСАНИЕ API

Проект предоставляет RESTful API для управления продажами. Поскольку в проекте настроен AllowAny для разрешений и отключена аутентификация, вы можете получить доступ к API без какой-либо авторизации.

Вы можете ознакомиться с полной интерактивной документацией API, используя Swagger UI.

Доступ к Swagger UI

После запуска сервера перейдите по адресу:

http://127.0.0.1:8000/swagger/

Здесь вы найдете полный список доступных эндпоинтов, их параметры, примеры запросов и ответов, а также сможете выполнять запросы непосредственно из браузера.

Примеры основных эндпоинтов (доступны через Swagger UI):

Управление клиентами:

GET /api/customers/: Получить список всех клиентов.

POST /api/customers/: Создать нового клиента.

GET /api/customers/{id}/: Получить детали клиента по ID.

PUT /api/customers/{id}/: Обновить данные клиента по ID.

DELETE /api/customers/{id}/: Удалить клиента по ID.

Управление продуктами:

GET /api/products/: Получить список всех продуктов.

POST /api/products/: Создать новый продукт.

GET /api/products/{id}/: Получить детали продукта по ID.

PUT /api/products/{id}/: Обновить данные продукта по ID.

DELETE /api/products/{id}/: Удалить продукт по ID.

Управление заказами:

GET /api/orders/: Получить список всех заказов.

POST /api/orders/: Создать новый заказ.

GET /api/orders/{id}/: Получить детали заказа по ID.

PUT /api/orders/{id}/: Обновить заказ по ID.

PATCH /api/orders/{id}/status/: Обновить статус заказа по ID (например, на confirmed).

Генерация отчетов:

GET /api/reports/sales/?start=YYYY-MM-DD&end=YYYY-MM-DD: Сгенерировать PDF-отчет по продажам за указанный период.

Пример: http://127.0.0.1:8000/api/reports/sales/?start=2023-01-01&end=2023-12-31

Пример запроса на создание заказа:
POST /api/orders/

JSON

{
    "customer_id": 1,
    "status": "draft",
    "delivery_cost": 500,
    "tax_percent": 12,
    "items": [
        {
            "product_id": 1,
            "quantity": 2
        },
        {
            "product_id": 2,
            "quantity": 1
        }
    ]
}
Пример запроса на обновление статуса заказа:
PATCH /api/orders/1/status/ (для заказа с ID 1)

JSON

{
    "status": "confirmed"
}
Примеры PDF-отчета
Пример PDF-отчета будет доступен для скачивания непосредственно по ссылке, сгенерированной вашим API. Например, после запуска сервера вы можете получить отчет, перейдя по следующему адресу (замените даты на нужный вам диапазон):

http://127.0.0.1:8000/api/reports/sales/?start=2023-01-01&end=2023-12-31

Можете использовать тестовые данные из файла test_data.json
