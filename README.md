# Telegram Timezone Bot

## Описание
Этот Telegram-бот позволяет пользователям выбирать континенты, страны и часовые пояса, а также узнавать текущее время в выбранной зоне. Бот написан на Python с использованием библиотеки `python-telegram-bot` и упакован в Docker для удобного развертывания.

---

## Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-repo/telegram-timezone-bot.git
cd telegram-timezone-bot
```

### 2. Установка зависимостей (локально)
Если хотите запустить бота без Docker, установите зависимости вручную:
```bash
pip install -r requirements.txt
```

### 3. Запуск бота (локально)
```bash
python bot.py
```

---

## Использование Docker

### 1. Установка Docker (если не установлен)
```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Сборка Docker-образа
```bash
docker build -t telegram-bot .
```

### 3. Запуск контейнера
```bash
docker run -d --name telegram-bot-container telegram-bot
```

### 4. Просмотр логов контейнера
```bash
docker logs -f telegram-bot-container
```

### 5. Остановка контейнера
```bash
docker stop telegram-bot-container
```

### 6. Перезапуск контейнера
```bash
docker start telegram-bot-container
```

### 7. Удаление контейнера
```bash
docker rm -f telegram-bot-container
```

---

## Переменные окружения
Бот использует переменную окружения `TOKEN` для хранения API-токена Telegram. Можно передавать её при запуске контейнера:
```bash
docker run -d --name telegram-bot-container -e TOKEN="your-telegram-token" telegram-bot
```

Или создать `.env` файл с содержимым:
```env
TOKEN=your-telegram-token
```
Затем использовать его в Docker:
```bash
docker run --env-file .env -d --name telegram-bot-container telegram-bot
```

---

## Файловая структура
```
telegram-timezone-bot/
├── bot.py            # Исходный код бота
├── requirements.txt   # Зависимости проекта
├── Dockerfile        # Инструкция для сборки Docker-образа
└── README.md         # Описание проекта
```

---

## Контакты и поддержка
Если у вас возникли вопросы или предложения, создайте issue в репозитории или свяжитесь с автором.

---

## Лицензия
Этот проект распространяется без лицензии.

