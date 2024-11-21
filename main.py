import random
import requests
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from config import TOKEN
import json
import os
import logging
import sqlite3

BOT_USERNAME: Final = '@Text_1233322_bot'
DATA_file = 'data.json'
WEIGHT, HEIGHT, AGE, GENDER, PRODUCTS = range(5)
DB_FILE = 'user_data.db'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                weight REAL,
                height REAL,
                age INTEGER,
                gender TEXT,
                bmr REAL,
                calories_consumed REAL
            )
        """)
        conn.commit()
        logger.info("База данных и таблица пользователей успешно инициализированы.")

def load_user_data(user_id):
    logger.info(f"Загрузка данных для пользователя {user_id}")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            data = {
                'weight': row[1],
                'height': row[2],
                'age': row[3],
                'gender': row[4],
                'bmr': row[5],
                'calories_consumed': row[6]
            }
            logger.info(f"Загруженные данные для пользователя {user_id}: {data}")
            return data
        else:
            logger.info(f"Нет данных для пользователя {user_id}")
            return {}

def save_user_data(user_id, user_data):
    logger.info(f"Сохранение данных для пользователя {user_id}: {user_data}")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, weight, height, age, gender, bmr, calories_consumed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET 
                weight=excluded.weight,
                height=excluded.height,
                age=excluded.age,
                gender=excluded.gender,
                bmr=excluded.bmr,
                calories_consumed=excluded.calories_consumed
        """, (user_id,
              user_data.get('weight'),
              user_data.get('height'),
              user_data.get('age'),
              user_data.get('gender'),
              user_data.get('bmr'),
              user_data.get('calories_consumed')))
        conn.commit()
    logger.info(f"Данные для пользователя {user_id} успешно сохранены.")

#Commands
async  def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Помогу тебе расчитать твой BMR\n'
                                    'используй команду /bmr')

async  def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Воспользуйся командами для различных действий.')


async def bmr_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Введите ваш вес в кг:')
    return WEIGHT

async def weight_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text)
        user_id = update.message.from_user.id
        user_data = load_user_data(user_id) or {}

        user_data['weight'] = weight
        logger.debug(f"Вес введен пользователем {user_id}: {weight}")
        save_user_data(user_id, user_data)

        await update.message.reply_text("Введите ваш рост в сантиметрах:")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное значение веса:")
        return WEIGHT


async def height_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text)
        user_id = update.message.from_user.id
        user_data = load_user_data(user_id) or {}

        user_data['height'] = height
        logger.debug(f"Рост введен пользователем {user_id}: {height}")
        save_user_data(user_id, user_data)

        await update.message.reply_text("Введите ваш возраст:")
        return AGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное значение роста:")
        return HEIGHT


async def age_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        user_id = update.message.from_user.id
        user_data = load_user_data(user_id) or {}

        user_data['age'] = age
        logger.debug(f"Возраст введен пользователем {user_id}: {age}")
        save_user_data(user_id, user_data)

        await update.message.reply_text("Введите ваш пол (мужской или женский):")
        return GENDER
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное значение возраста:")
        return AGE
async def gender_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gender = update.message.text.lower()
    user_id = update.message.from_user.id
    user_data = load_user_data(user_id) or {}

    logger.debug(f"Пол введен пользователем {user_id}: {gender}")

    if gender in ['мужской', 'женский']:
        user_data['gender'] = gender

        weight = user_data.get('weight')
        height = user_data.get('height')
        age = user_data.get('age')

        if weight is not None and height is not None and age is not None:
            bmr = calculate_bmr(weight, height, age, gender)
            user_data['bmr'] = bmr
            user_data['calories_consumed'] = 0
            logger.debug(f"Рассчитанный BMR для пользователя {user_id}: {bmr}")
            save_user_data(user_id, user_data)

            await update.message.reply_text(f"Ваш BMR: {bmr:.2f} ккал в день.")
        else:
            missing_fields = []
            if weight is None:
                missing_fields.append('weight')
            if height is None:
                missing_fields.append('height')
            if age is None:
                missing_fields.append('age')
            logger.error(f"Отсутствуют данные: {', '.join(missing_fields)} для пользователя {user_id}")
            await update.message.reply_text(
                f"Ошибка: отсутствуют данные {', '.join(missing_fields)}. Попробуйте заново.")
            return WEIGHT

        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, введите корректное значение пола (male или female):")
        return GENDER

def calculate_bmr(weight, height, age, gender):
    if gender == 'мужской':
        return 10*weight + 6.25*height - 5*age + 5
    else:
        return 10*weight + 6.25*height - 5*age - 161
async def calories_command(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        'Введите продукты и их вес в формате "продукт1-вес1 (в граммах), продукт2-вес2 (в граммах), ..."'
    )
    return PRODUCTS


async def calculate_calories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    input_text = update.message.text
    product_list = []

    try:
        items = input_text.split(',')
        for item in items:
            product, weight = item.split('-')
            product_list.append((product.strip(), float(weight.strip())))
    except Exception:
        await update.message.reply_text(
            'Ошибка ввода. Пожалуйста, используйте формат "продукт1-вес1 (в граммах), продукт2-вес2 (в граммах), ...".'
        )
        return PRODUCTS

    total_calories = calculate_total_calories(product_list)
    user_data = load_user_data(user_id)
    if user_data:
        user_data['calories_consumed'] += total_calories
        save_user_data(user_id, user_data)

        remaining_calories = user_data['bmr'] - user_data['calories_consumed']
        if remaining_calories > 0:
            await update.message.reply_text(
                f'Вы потребили {total_calories:.2f} ккал. Осталось: {remaining_calories:.2f} ккал.'
            )
        else:
            await update.message.reply_text(
                f'Вы потребили {total_calories:.2f} ккал. Вы превысили норму на {-remaining_calories:.2f} ккал!'
            )

    return ConversationHandler.END

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
    await update.message.reply_text("Ваши данные сброшены. Вы можете заново рассчитать BMR с помощью команды /bmr.")

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Действие отменено.')
    return ConversationHandler.END


def get_product_code(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get('products'):
            return data['products'][0]['code']  # Возвращаем первый найденный штрих-код
        else:
            return None
    else:
        return None


def get_calories(product_name, weight):
    product_code = get_product_code(product_name)
    if not product_code:
        return 0
    url = f"https://world.openfoodfacts.org/api/v0/product/{product_code}.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get('product') and data['product'].get('nutriments'):
            nutriments = data['product']['nutriments']
            calories_per_100g = nutriments.get('energy-kcal_100g')
            if calories_per_100g:
                calories = (calories_per_100g * weight) / 100
                return calories
            else:
                return 0
        else:
            return 0
    else:
        return 0


def calculate_total_calories(product_list):
    total_calories = 0
    for product_name, weight in product_list:
        calories = get_calories(product_name, weight)
        total_calories += calories
    return total_calories

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    initialize_db()
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Conversation handler for /calories
    calories_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('calories', calories_command)],
        states={
            PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_calories)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    bmr_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('bmr', bmr_start)],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_input)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_input)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_input)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(calories_conv_handler)
    app.add_handler(bmr_conv_handler)
    #Command
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler("reset", reset_command))

    #Errors
    app.add_error_handler(error)
    #Polls the bot
    print('Polling')
    app.run_polling(poll_interval=5)