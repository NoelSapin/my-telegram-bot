# region Импорты
import logging
from datetime import datetime, time
import re

import pytz
import pycountry
import pycountry_convert

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters
)
from telegram.error import BadRequest
# endregion


# region Глобальные данные
TOKEN = "8102873395:AAGcgCPORaDFKj6DdylLL9O1AuSjQuMkyZc"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# endregion


# region Обработчик ошибок
def error_handler(update: object, context: CallbackContext):
    logger.error("Произошла ошибка: %s", context.error)
# endregion


# region Подготовка структуры (континент → страна → список таймзон)
def get_continent_name(alpha2: str) -> str:
    """
    Конвертируем код страны (например, 'RU') в название континента ('Europe').
    Если не выходит — возвращаем 'Unknown'.
    """
    try:
        code = pycountry_convert.country_alpha2_to_continent_code(alpha2)
        mapping = {
            'AF': 'Africa',
            'AS': 'Asia',
            'EU': 'Europe',
            'NA': 'North America',
            'SA': 'South America',
            'OC': 'Oceania',
            'AN': 'Antarctica'
        }
        return mapping.get(code, 'Unknown')
    except:
        return 'Unknown'


def build_data_structure():
    """
    Создаёт словарь вида:
    {
        "Europe": {
            "Russia": ["Europe/Moscow", "Europe/Kaliningrad", ...],
            "France": [...],
            ...
        },
        "Asia": {...},
        ...
    }
    """
    result = {}
    all_countries = list(pycountry.countries)

    for country in all_countries:
        alpha2 = country.alpha_2
        # Пропускаем, если у страны нет таймзон в pytz
        if alpha2 not in pytz.country_timezones:
            continue

        tz_list = pytz.country_timezones[alpha2]
        if not tz_list:
            continue

        continent = get_continent_name(alpha2)
        if continent not in result:
            result[continent] = {}
        result[continent][country.name] = tz_list

    return result


DATA = build_data_structure()
# endregion


# region Построение клавиатуры (универсальный подход)
def build_keyboard(path: str) -> InlineKeyboardMarkup:
    """
    Генерирует InlineKeyboardMarkup исходя из того, сколько «элементов» в path.
    path — строка вида "Asia", или "Asia;Russia", или "Asia;Russia;Asia/Novosibirsk", и т.д.
    Пустая строка означает, что мы на «корневом» уровне (континенты).
    """
    parts = path.split(';') if path else []
    level = len(parts)

    keyboard = []

    # Уровень 0 → показываем континенты
    if level == 0:
        for cont in sorted(DATA.keys()):
            keyboard.append([InlineKeyboardButton(
                text=cont,
                callback_data=cont  # например, "Europe"
            )])
    # Уровень 1 → показываем страны данного континента
    elif level == 1:
        continent = parts[0]
        for country_name in sorted(DATA.get(continent, {}).keys()):
            new_path = f"{continent};{country_name}"
            keyboard.append([InlineKeyboardButton(
                text=country_name,
                callback_data=new_path
            )])
    # Уровень 2 → показываем таймзоны выбранной страны
    elif level == 2:
        continent, country = parts
        for tz_name in sorted(DATA.get(continent, {}).get(country, [])):
            new_path = f"{continent};{country};{tz_name}"
            caption = tz_name.split('/')[-1] if '/' in tz_name else tz_name
            keyboard.append([InlineKeyboardButton(
                text=caption,
                callback_data=new_path
            )])
    # Уровень 3 → можно добавить дополнительные кнопки (например, для дальнейших действий)
    elif level == 3:
        # Пока оставляем пустым
        pass

    # Добавляем кнопку «Назад», если есть куда возвращаться
    if level > 0:
        back_path = ';'.join(parts[:-1])
        # Если мы переходим на корневой уровень, callback_data не может быть пустой – назначаем специальное значение "ROOT"
        if not back_path:
            back_path = "ROOT"
        keyboard.append([InlineKeyboardButton("<< Назад", callback_data=back_path)])

    return InlineKeyboardMarkup(keyboard)
# endregion


# region Хендлер для callback (обработка нажатий на кнопки)
async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    raw_path = query.data  # например, "Europe;Russia;Europe/Moscow" или ""
    await safe_answer(query)  # чтобы Telegram "не ругался"

    # Если получили "ROOT", трактуем как корневой уровень
    if raw_path == "ROOT":
        raw_path = ""
    parts = raw_path.split(';') if raw_path else []
    level = len(parts)

    # Если ничего нет (level=0) – показываем континенты
    if level == 0:
        await query.edit_message_text(
            text="Выберите континент:",
            reply_markup=build_keyboard("")
        )
        return

    # Если 1 элемент → выбираем страну
    if level == 1:
        continent = parts[0]
        await query.edit_message_text(
            text=f"Континент: {continent}\nВыберите страну:",
            reply_markup=build_keyboard(raw_path)
        )
        return

    # Если 2 элемента → выбираем таймзону
    if level == 2:
        continent, country = parts
        await query.edit_message_text(
            text=f"Страна: {country}\nВыберите город/таймзону:",
            reply_markup=build_keyboard(raw_path)
        )
        return

    # Если 3 элемента → показываем текущее время в выбранной таймзоне
    if level == 3:
        continent, country, tz_name = parts
        now_local = datetime.now(pytz.timezone(tz_name)).strftime("%H:%M")
        msg_text = f"Текущее время в {tz_name}:\n{now_local}"
        await query.edit_message_text(
            text=msg_text,
            reply_markup=build_keyboard(raw_path)
        )
        return

    # Если уровень не распознан – возвращаемся в начало
    await query.edit_message_text(
        text="Что-то пошло не так. Возвращаемся в начало...",
        reply_markup=build_keyboard("")
    )


async def safe_answer(query):
    """Ответить на коллбэк, игнорируя ошибку 'query is too old'."""
    try:
        await query.answer()
    except BadRequest as e:
        if "query is too old" in str(e).lower():
            return
        raise
# endregion


# region Хендлеры текстовых сообщений (поиск ближайшего времени)
def extract_time_from_message(message: str) -> time | None:
    """
    Ищем в сообщении время (форматы: 18:00, 18.00, 18,00, 18 00).
    Возвращаем time или None, если не найдено.
    """
    pattern = r"(\d{1,2}[:., ]\d{1,2})"
    match = re.search(pattern, message)
    if not match:
        return None

    timestr = match.group(1)
    for sep in ('.', ',', ' '):
        timestr = timestr.replace(sep, ':')

    try:
        return datetime.strptime(timestr, "%H:%M").time()
    except ValueError:
        return None


def find_closest_timezones(target_time: time, top_n=3):
    """
    Возвращаем список [(tz_name, diff), ...] — у каких таймзон локальное время
    ближе всего к target_time (сейчас).
    """
    now_utc = datetime.now(pytz.utc)
    target_minutes = target_time.hour * 60 + target_time.minute
    diffs = []

    for cont, countries in DATA.items():
        for country_name, tz_list in countries.items():
            for tz_name in tz_list:
                local_dt = now_utc.astimezone(pytz.timezone(tz_name))
                local_minutes = local_dt.hour * 60 + local_dt.minute
                diff = abs(local_minutes - target_minutes)
                diffs.append((tz_name, diff))

    diffs.sort(key=lambda x: x[1])
    return diffs[:top_n]


async def handle_text_message(update: Update, context: CallbackContext):
    user_msg = update.message.text.strip()
    t = extract_time_from_message(user_msg)
    if not t:
        await update.message.reply_text("Не понял время. Введите, например, 18:00.")
        return

    close_list = find_closest_timezones(t, top_n=3)
    formatted = ", ".join(tz for tz, _ in close_list)
    text_out = (
        f"Вы ввели время {t.strftime('%H:%M')}.\n"
        f"Ближе всего к этому сейчас: {formatted}"
    )
    await update.message.reply_text(text_out)
# endregion


# region Команды (/start, /time)
async def cmd_start(update: Update, context: CallbackContext):
    """
    Команда /start — показать «корневой» уровень (список континентов)
    """
    await update.message.reply_text(
        text="Привет! Выберите континент или введите время (например 18:00).",
        reply_markup=build_keyboard("")
    )


async def cmd_time(update: Update, context: CallbackContext):
    """
    Команда /time — демонстрация: выводим текущее время в нескольких первых таймзонах
    (по 1-2 страны с каждого континента).
    """
    lines = []
    for cont, countries in DATA.items():
        for c_name, tz_list in list(countries.items())[:2]:
            if not tz_list:
                continue
            tz = tz_list[0]
            now_loc = datetime.now(pytz.timezone(tz)).strftime("%H:%M")
            lines.append(f"{cont} / {c_name} / {tz} → {now_loc}")

    if lines:
        await update.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text("Нет данных.")
# endregion


# region MAIN
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("time", cmd_time))

    # Inline-кнопки
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Текстовые сообщения (ищем время)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    app.run_polling()


if __name__ == "__main__":
    main()
# endregion
