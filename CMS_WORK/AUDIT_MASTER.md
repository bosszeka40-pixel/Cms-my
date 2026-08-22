# CMS_WORK — Strict Full Audit Master

## Статус
Начат строгий аудит проекта Daily Compound Harvester CMS.

## Цели аудита
- Проверка архитектуры backend/frontend.
- Проверка связей модулей и зависимостей.
- Поиск ошибок логики, безопасности и разрывов интеграций.
- Создание карты веток, функций и потоков данных.
- Подготовка карты полной логики работы CMS.

## Обнаружено на первом проходе

### Архитектура
Проект заявляет структуру:
- backend — FastAPI ядро
- cms_core — база и модели
- admin — управление пользователями и плагинами
- bot — управление торговым блоком
- hft_brain — AI/торговая логика
- modules — стратегии
- frontend — интерфейс

Источник: README.md.

### Первичные зоны проверки

1. Backend API:
- соответствие маршрутов реализации;
- обработка ошибок;
- валидация входных данных;
- состояние процессов бота.

2. Trading Engine:
- безопасность live режима;
- разделение тест/реальная торговля;
- корректность расчётов прибыли и риска;
- проверка стратегий.

3. Database:
- модели;
- миграции;
- сохранение памяти обучения;
- целостность данных.

4. Deployment:
- Docker;
- облачные настройки;
- переменные окружения;
- секреты.

## Карта логики (черновик)

User → Frontend → API Router → CMS Core → Modules

Trading flow:
Market Data → Analysis → Strategy Engine → Risk Control → Order Layer → Exchange

AI flow:
History → Learning Memory → AI Brain → Signal Generation → Report

## Следующие этапы

- Полный разбор всех файлов backend.
- Проверка каждой функции.
- Создание FUNCTION_MAP.md.
- Создание BRANCH_MAP.md.
- Создание SYSTEM_CONNECTION_MAP.md.
- Формирование списка ошибок с приоритетами Critical/High/Medium/Low.
