import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import calendar
import time

bot = telebot.TeleBot('7835306572:AAGIi_1aCIJciSYY-B78-Z9vgPQr_ckFfIw')  # Замените на реальный токен


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('planner.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL,
                     title TEXT NOT NULL,
                     priority INTEGER DEFAULT 1,
                     category TEXT,
                     deadline TEXT,
                     created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                     time_spent INTEGER DEFAULT 0,
                     status TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()


init_db()

# Состояния пользователей
user_states = {}


# Клавиатуры
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('📝 Добавить задачу', '📋 Мои задачи')
    markup.row('⚙️ Настройки')
    return markup


def cancel_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('❌ Отмена')
    return markup


def generate_calendar(year=None, month=None):
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month

    markup = types.InlineKeyboardMarkup()

    # Заголовок
    month_name = calendar.month_name[month]
    markup.row(types.InlineKeyboardButton(
        f"{month_name} {year}",
        callback_data="ignore"
    ))

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    markup.row(*[types.InlineKeyboardButton(
        day, callback_data="ignore"
    ) for day in week_days])

    # Дни месяца
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(
                    " ", callback_data="ignore"
                ))
            else:
                row.append(types.InlineKeyboardButton(
                    str(day),
                    callback_data=f"day_{year}_{month}_{day}"
                ))
        markup.row(*row)

    # Навигация
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

    markup.row(
        types.InlineKeyboardButton(
            "◀",
            callback_data=f"prev_{prev_year}_{prev_month}"
        ),
        types.InlineKeyboardButton(
            "▶",
            callback_data=f"next_{next_year}_{next_month}"
        )
    )

    markup.row(types.InlineKeyboardButton(
        "❌ Без срока",
        callback_data="no_deadline"
    ))

    return markup


def generate_hour_selector(selected_date):
    markup = types.InlineKeyboardMarkup(row_width=6)

    # Часы с 00 до 23
    hours = []
    for hour in range(0, 24):
        hours.append(types.InlineKeyboardButton(
            f"{hour:02d}",
            callback_data=f"hour_{selected_date}_{hour}"
        ))

    # Разбиваем на 4 ряда по 6 кнопок
    for i in range(0, len(hours), 6):
        markup.row(*hours[i:i + 6])

    markup.row(types.InlineKeyboardButton(
        "❌ Отмена",
        callback_data="cancel_time"
    ))

    return markup


def generate_minute_selector(selected_date, hour):
    markup = types.InlineKeyboardMarkup(row_width=4)

    # Минуты с шагом 15
    minutes = ['00', '15', '30', '45']
    for minute in minutes:
        markup.add(types.InlineKeyboardButton(
            minute,
            callback_data=f"time_{selected_date}_{hour}_{minute}"
        ))

    # Быстрый выбор
    markup.row(
        types.InlineKeyboardButton(
            "🌅 Утро (09:00)",
            callback_data=f"time_{selected_date}_9_00"
        ),
        types.InlineKeyboardButton(
            "🏙 День (14:00)",
            callback_data=f"time_{selected_date}_14_00"
        )
    )
    markup.row(
        types.InlineKeyboardButton(
            "🌃 Вечер (19:00)",
            callback_data=f"time_{selected_date}_19_00"
        ),
        types.InlineKeyboardButton(
            "❌ Отмена",
            callback_data="cancel_time"
        )
    )

    return markup


# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "📅 Привет! Я твой умный планировщик задач.\n"
        "Выбери действие в меню ниже:",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda m: m.text == '📝 Добавить задачу')
def add_task(message):
    msg = bot.send_message(
        message.chat.id,
        "📌 Введите название задачи:",
        reply_markup=cancel_menu()
    )
    bot.register_next_step_handler(msg, process_task_name)


def process_task_name(message):
    if message.text == '❌ Отмена':
        bot.send_message(
            message.chat.id,
            "Действие отменено",
            reply_markup=main_menu()
        )
        return

    user_states[message.chat.id] = {'title': message.text}
    msg = bot.send_message(
        message.chat.id,
        "🔢 Оцените важность задачи (1-5):\n"
        "1 - низкий, 5 - очень важный",
        reply_markup=cancel_menu()
    )
    bot.register_next_step_handler(msg, process_task_priority)


def process_task_priority(message):
    if message.text == '❌ Отмена':
        bot.send_message(
            message.chat.id,
            "Действие отменено",
            reply_markup=main_menu()
        )
        return

    if not message.text.isdigit() or int(message.text) not in range(1, 6):
        msg = bot.send_message(
            message.chat.id,
            "Пожалуйста, введите число от 1 до 5:",
            reply_markup=cancel_menu()
        )
        bot.register_next_step_handler(msg, process_task_priority)
        return

    user_states[message.chat.id]['priority'] = int(message.text)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Работа', 'Учёба', 'Личное', 'Другое', '❌ Отмена')

    msg = bot.send_message(
        message.chat.id,
        "🏷 Выберите категорию задачи:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_task_category)


def process_task_category(message):
    if message.text == '❌ Отмена':
        bot.send_message(
            message.chat.id,
            "Действие отменено",
            reply_markup=main_menu()
        )
        return

    if message.text not in ['Работа', 'Учёба', 'Личное', 'Другое']:
        msg = bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите категорию из предложенных:",
            reply_markup=types.ReplyKeyboardMarkup(
                resize_keyboard=True
            ).add('Работа', 'Учёба', 'Личное', 'Другое', '❌ Отмена')
        )
        bot.register_next_step_handler(msg, process_task_category)
        return

    user_states[message.chat.id]['category'] = message.text
    now = datetime.now()
    bot.send_message(
        message.chat.id,
        "📅 Выберите дату выполнения:",
        reply_markup=generate_calendar(now.year, now.month)
    )


# Обработка календаря
@bot.callback_query_handler(func=lambda call: call.data.startswith(('prev_', 'next_')))
def navigate_calendar(call):
    try:
        _, year, month = call.data.split('_')
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=generate_calendar(int(year), int(month))
        )
    except Exception as e:
        print(f"Error in navigate_calendar: {e}")
    finally:
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('day_'))
def select_date(call):
    try:
        _, year, month, day = call.data.split('_')
        selected_date = f"{year}-{int(month):02d}-{int(day):02d}"
        user_states[call.message.chat.id]['deadline_date'] = selected_date

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📅 Выбрана дата: {day}.{month}.{year}\n"
                 "⏰ Теперь выберите час:",
            reply_markup=generate_hour_selector(selected_date))
    except Exception as e:
        print(f"Error in select_date: {e}")
    finally:
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('hour_'))
def select_hour(call):
    try:
        _, date, hour = call.data.split('_')
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⏰ Выберите минуты для {hour}:00",
            reply_markup=generate_minute_selector(date, hour))
    except Exception as e:
        print(f"Error in select_hour: {e}")
    finally:
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'no_deadline')
def no_deadline(call):
    try:
        save_task(call.message.chat.id, None)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ Задача добавлена без срока!")
        bot.send_message(
            call.message.chat.id,
            "Главное меню:",
            reply_markup=main_menu()
        )
    except Exception as e:
        print(f"Error in no_deadline: {e}")
    finally:
        bot.answer_callback_query(call.id)


# Обработка времени
@bot.callback_query_handler(func=lambda call: call.data.startswith('time_') or call.data == 'cancel_time')
def handle_time_selection(call):
    try:
        if call.data == 'cancel_time':
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Выбор времени отменен"
            )
            return

        _, date, hour, minute = call.data.split('_')
        deadline = f"{date} {hour}:{minute}:00"
        save_task(call.message.chat.id, deadline)

        formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Задача добавлена!\n"
                 f"⏰ Срок: {formatted_date} в {hour}:{minute}"
        )
        bot.send_message(
            call.message.chat.id,
            "Главное меню:",
            reply_markup=main_menu()
        )
    except Exception as e:
        print(f"Error in handle_time_selection: {e}")
    finally:
        bot.answer_callback_query(call.id)


def save_task(chat_id, deadline):
    try:
        if chat_id not in user_states:
            return

        data = user_states[chat_id]

        conn = sqlite3.connect('planner.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO tasks 
                         (user_id, title, priority, category, deadline)
                         VALUES (?, ?, ?, ?, ?)''',
                       (chat_id,
                        data['title'],
                        data['priority'],
                        data['category'],
                        deadline))
        conn.commit()
    except Exception as e:
        print(f"Error saving task: {e}")
    finally:
        conn.close()
        if chat_id in user_states:
            del user_states[chat_id]


@bot.message_handler(func=lambda m: m.text == '📋 Мои задачи')
def show_tasks(message):
    try:
        conn = sqlite3.connect('planner.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, title, priority, category, deadline 
                         FROM tasks 
                         WHERE user_id=? AND status='pending'
                         ORDER BY deadline''',
                       (message.chat.id,))

        tasks = cursor.fetchall()

        if not tasks:
            bot.send_message(
                message.chat.id,
                "У вас нет активных задач!",
                reply_markup=main_menu()
            )
            return

        response = "📋 Ваши задачи:\n\n"
        for task in tasks:
            deadline = "нет срока"
            if task[4]:
                deadline_dt = datetime.strptime(task[4], "%Y-%m-%d %H:%M:%S")
                deadline = deadline_dt.strftime("%d.%m.%Y %H:%M")

            response += (f"📌 {task[1]}\n"
                         f"⭐ Важность: {task[2]}/5\n"
                         f"🏷 Категория: {task[3]}\n"
                         f"⏰ Срок: {deadline}\n"
                         f"❌ Удалить: /del_{task[0]}\n"
                         f"✅ Завершить: /done_{task[0]}\n\n")

        bot.send_message(
            message.chat.id,
            response,
            reply_markup=main_menu()
        )
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")
    finally:
        conn.close()


@bot.message_handler(func=lambda m: m.text.startswith('/del_'))
def delete_task(message):
    try:
        task_id = message.text.split('_')[1]

        conn = sqlite3.connect('planner.db')
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM tasks 
                         WHERE id=? AND user_id=?''',
                       (task_id, message.chat.id))

        if cursor.rowcount == 0:
            bot.reply_to(message, "Задача не найдена!")
        else:
            conn.commit()
            bot.reply_to(message, "🗑 Задача удалена!")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")
    finally:
        conn.close()


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)