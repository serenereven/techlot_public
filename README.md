# Techlot

Django-приложение для каталога спецтехники с интеграцией с Bitrix24 и SberLeasing.

Проект синхронизирует каталог между Bitrix24 и локальной базой данных, обрабатывает события асинхронно и предоставляет публичный каталог техники.

## Что реализовано

* интеграция с Bitrix24 REST API;
* обработка webhook-событий каталога;
* асинхронная синхронизация через Celery;
* дедупликация повторных webhook-событий через Redis;
* локальный каталог спецтехники на Django;
* импорт данных из XLSX;
* экспорт каталога в XLSX;
* автоматическое обновление цен из SberLeasing;
* Django Admin для управления каталогом;
* sitemap и публичные страницы каталога;
* тесты интеграции с Bitrix24.

## Архитектура

Основной сценарий синхронизации выглядит так:

```text id="q7f3kd"
Bitrix24
    │
    │ webhook
    ▼
Django
    │
    │ проверка + дедупликация
    ▼
Celery
    │
    │ Bitrix24 REST API
    ▼
Sync / Mapper
    │
    ▼
Django ORM
    │
    ▼
PostgreSQL
```

Webhook только принимает событие и ставит задачу в очередь. Синхронизация выполняется отдельно в Celery worker, поэтому запрос к Bitrix24 и обновление локальных данных не блокируют HTTP-обработчик.

Для повторных событий используется Redis cache: перед постановкой задачи приложение проверяет, не обрабатывался ли уже соответствующий event.

## Bitrix24

Интеграция вынесена в отдельный сервисный слой.

```text id="j6h2sa"
core/services/bitrix/
├── catalog.py
├── client.py
├── exceptions.py
├── lead.py
├── mapper.py
└── sync.py
```

`client` отвечает за работу с API, `mapper` преобразует данные Bitrix24, а `sync` применяет изменения к локальным моделям.

Приложение обрабатывает события добавления и обновления товаров каталога Bitrix24.

## Обновление цен

Для обновления цен используется интеграция с SberLeasing.

Обновление выполняется фоновой задачей Celery, которая получает данные из XML-фида и обновляет цены существующих позиций каталога.

Задача запускается автоматически через Celery Beat.

## Импорт и экспорт

Каталог можно импортировать из XLSX и экспортировать обратно в XLSX.

Импорт поддерживает обновление существующих записей по VIN и создание отсутствующих записей.

Экспорт реализован в `core/export_utils.py`.

## Стек

**Backend**

* Python
* Django
* PostgreSQL
* Celery
* Redis

**Интеграции**

* Bitrix24 REST API
* SberLeasing XML feed

**Infrastructure**

* Docker
* Docker Compose

**Testing**

* pytest

## Запуск

Требуются Docker и Docker Compose.

```bash id="y8zv2m"
git clone https://github.com/serenereven/techlot_public.git
cd techlot_public

cp .env.example .env
```

Заполните необходимые переменные окружения и запустите проект:

```bash id="t5n8wq"
docker-compose up --build
```

После запуска:

```bash id="p1s6cx"
docker-compose exec web python manage.py migrate
```

Приложение доступно на `http://localhost:8000`.

## Тесты

```bash id="v2r9mx"
docker-compose exec web pytest
```

Основные интеграционные тесты находятся в `tests/` и покрывают преобразование данных Bitrix24 и синхронизацию каталога.

## Лицензия

MIT
