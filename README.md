# Techlot — Каталог спецтехники с интеграцией Bitrix24

Django-проект каталога техники с полной синхронизацией с Bitrix24, управлением контентом и экспортом данных.

## 🚀 Особенности

- **Полная синхронизация с Bitrix24** — двусторонняя синхронизация товаров через вебхуки и REST API
- **Real-time обновления** — обработка событий Bitrix через Celery + Redis
- **Мягкое удаление (Soft Delete)** — сохранение истории без физического удаления записей
- **SEO-оптимизация** — автогенерация slug, мета-тегов, sitemap
- **Экспорт данных** — выгрузка каталога в XML/CSV для интеграций
- **Антидублирование** — защита от повторной обработки событий через Redis cache
- **Миксины для моделей** — переиспользуемые компоненты (UUID, timestamps, publishable)

## 📚 Стек технологий

| Категория | Технологии |
|-----------|------------|
| **Backend** | Django 5.2.8, Python 3.10+ |
| **Database** | PostgreSQL 14+ |
| **Cache/Broker** | Redis 7+ |
| **Task Queue** | Celery 5.3+, Celery Beat |
| **Integration** | Bitrix24 REST API, Webhooks |
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Deployment** | Docker, Docker Compose |
| **Testing** | pytest, pytest-django |

## 🏗 Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Bitrix24  │────▶│  Webhooks    │────▶│   Celery    │
│   Catalog   │     │  (Django)    │     │   Tasks     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   PostgreSQL │     │    Redis    │
                    │   (Storage)  │     │ (Cache/Queue)│
                    └──────────────┘     └─────────────┘
```

### Структура проекта

```
/workspace
├── core/                    # Основное приложение
│   ├── models.py           # Модели (Vehicle, Brand, City и т.д.)
│   ├── views.py            # Views для каталога и экспорта
│   ├── webhooks.py         # Обработчики вебхуков Bitrix
│   ├── tasks.py            # Celery задачи для синхронизации
│   ├── services/bitrix/    # Сервисный слой для работы с Bitrix
│   │   ├── client.py       # HTTP-клиент с retry logic
│   │   ├── mapper.py       # Маппинг полей Bitrix → Django
│   │   └── sync.py         # Логика синхронизации
│   └── admin.py            # Настройка админки
├── common/                  # Общие модели и утилиты
│   └── models/             # Миксины (UUID, SoftDelete, Publishable)
├── techlot/                 # Настройки проекта
│   └── settings.py         # Конфигурация Django
├── tests/                   # Тесты
│   ├── test_mapper.py      # Тесты маппинга Bitrix
│   └── test_sync.py        # Тесты синхронизации
├── docker-compose.yml       # Оркестрация контейнеров
├── Dockerfile              # Образ приложения
└── requirements.txt        # Зависимости Python
```

## 🛠 Быстрый старт

### Требования

- Docker 20+
- Docker Compose 2.0+
- Git

### Установка

1. **Клонируйте репозиторий**
   ```bash
   git clone <repository-url>
   cd techlot
   ```

2. **Создайте файл окружения**
   ```bash
   cp .env.example .env
   ```

3. **Настройте переменные окружения**

   Отредактируйте `.env`:
   ```env
   # Django
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   
   # База данных
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=techlot_db
   DB_USER=techlot_user
   DB_PASSWORD=strong-password-here
   DB_HOST=db
   DB_PORT=5432
   
   # Redis
   REDIS_URL=redis://redis:6379/0
   
   # Bitrix24 (получите в настройках Bitrix)
   BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/1/webhook-code/
   BITRIX_CATALOG_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/1/catalog-webhook/
   BITRIX_INCOMING_TOKEN=your-incoming-token
   ```

4. **Запустите проект**
   ```bash
   docker-compose up -d --build
   ```

5. **Выполните миграции**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

6. **Создайте суперпользователя**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

7. **Соберите статику**
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

Проект доступен по адресу: `http://localhost:8000`  
Админка: `http://localhost:8000/admin`

## 📋 Основные команды

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f web
docker-compose logs -f celery

# Остановка проекта
docker-compose down

# Выполнение миграций
docker-compose exec web python manage.py migrate

# Запуск тестов
docker-compose exec web pytest

# Создание бэкапа БД
docker-compose exec db pg_dump -U techlot_user techlot_db > backup.sql
```

## 🔌 Интеграция с Bitrix24

### Настройка вебхуков

1. В Bitrix24 перейдите в **Разработчикам → Другие настройки → Входящие вебхуки**
2. Создайте вебхук с правами:
   - `catalog`
   - `task`
3. Скопируйте URL вебхука в `.env` как `BITRIX_CATALOG_WEBHOOK_URL`

### Регистрация событий

При установке приложения (событие `ONAPPINSTALL`) проект автоматически подписывается на события:
- `CATALOG.PRODUCT.ON.ADD` — добавление товара
- `CATALOG.PRODUCT.ON.UPDATE` — обновление товара

### Синхронизация данных

Вебхук получает событие → сохраняет в Redis cache (anti-duplicate) → отправляет задачу в Celery → задача вызывает Bitrix API → обновляет модель `Vehicle`.

## 🧪 Тестирование

```bash
# Запустить все тесты
docker-compose exec web pytest

# Запустить с покрытием
docker-compose exec web pytest --cov=.

# Запустить конкретный тест
docker-compose exec web pytest tests/test_mapper.py -v
```

## 📊 Модели данных

### Основные модели

| Модель | Описание |
|--------|----------|
| `Vehicle` | Карточка техники (основная) |
| `Brand` | Марка техники |
| `VehicleModel` | Модель техники |
| `City` / `Region` | География |
| `VehiclePhoto` | Фотографии техники |
| `PurchaseRequest` | Заявки на покупку |
| `Contact` | Контакты компании |

### Статусы техники

- `awaiting` — В ожидании поступления
- `in_stock` — В наличии
- `reserved` — В резерве
- `leasing` — Продажа в лизинг
- `sold` — Продано

## 🔐 Безопасность

- Все чувствительные данные вынесены в переменные окружения
- CSRF protection включен
- SSL redirect настраивается через `DJANGO_SECURE_SSL_REDIRECT`
- Секретные токены Bitrix хранятся в `.env`

**Важно:** Никогда не коммитьте файл `.env` в репозиторий!

## 📈 Производительность

- Кэширование запросов к Bitrix (TTL настраивается)
- Антидублирование событий через Redis
- Асинхронная обработка через Celery
- Оптимизированные индексы в БД
- Select_related/prefetch_related для сложных запросов

## 🎯 API Endpoints

### Публичные

- `GET /` — Главная страница
- `GET /catalog/` — Каталог техники
- `GET /catalog/<slug>/` — Детальная страница техники
- `GET /export/vehicles.xml` — Экспорт в XML
- `GET /export/vehicles.csv` — Экспорт в CSV

### Вебхуки

- `POST /webhooks/bitrix/catalog/<token>/` — Обработка событий Bitrix

## 📝 Лицензия

MIT License — см. файл [LICENSE](LICENSE)

## 👥 Контакты

Разработчик: [Ваше имя]  
Email: [your.email@example.com]  
Telegram: [@yourusername]

---

**Статус проекта:** Production Ready ✅  
**Последнее обновление:** 2024
