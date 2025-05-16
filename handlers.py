import sqlite3
import aiohttp
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from database import get_theaters, get_performances, buy_ticket

logger = logging.getLogger(__name__)

SELECTING_ACTION, CHOOSING_THEATER, BUYING_TICKET = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал взаимодействие")

    context.user_data.clear()
    await update.message.reply_text(
        f"Привет, {user.first_name}!\nДобро пожаловать в театральный бот!",
        reply_markup=ReplyKeyboardMarkup([["Список театров"]], resize_keyboard=True)
    )
    return SELECTING_ACTION


async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    if text == "Список театров":
        if theaters := get_theaters():
            theater_names = [t[1] for t in theaters]
            keyboard = [theater_names[i:i + 2] for i in range(0, len(theater_names), 2)]
            keyboard.append(["Назад"])

            context.user_data['theaters'] = {t[1]: t[0] for t in theaters}

            await update.message.reply_text(
                "Выберите театр:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return CHOOSING_THEATER
        else:
            await update.message.reply_text("Театры не найдены")
            return SELECTING_ACTION

    elif text == "Назад":
        return await start(update, context)

    await update.message.reply_text("Пожалуйста, используйте кнопки")
    return SELECTING_ACTION


async def choose_theater(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text

        if text == "Назад":
            return await select_action(update, context)

        if 'theaters' not in context.user_data or text not in context.user_data['theaters']:
            await update.message.reply_text("Пожалуйста, выберите театр из списка")
            return CHOOSING_THEATER

        theater_id = context.user_data['theaters'][text]
        performances = get_performances(theater_id)

        if not performances:
            await update.message.reply_text("Нет доступных спектаклей")
            return CHOOSING_THEATER

        conn = sqlite3.connect("theater_tickets.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, address, latitude, longitude FROM theaters WHERE id = ?",
            (theater_id,)
        )
        name, address, lat, lon = cursor.fetchone()
        conn.close()

        map_url = f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&size=450,450&z=16&l=map&pt={lon},{lat},pm2rdl"
        try:
            async with aiohttp.ClientSession() as session:
                if (resp := await session.get(map_url)).status == 200:
                    await context.bot.send_photo(
                        chat_id=update.message.chat_id,
                        photo=map_url,
                        caption=f"📍 {name}\n🏛 {address}"
                    )
        except Exception as e:
            logger.error(f"Ошибка карты: {e}")
            await update.message.reply_text(f"Адрес театра: {address}")

        context.user_data['current_performances'] = {str(p[0]): p for p in performances}
        performances_msg = "\n\n".join(
            f"🎭 {p[1]}\n📅 {p[2]} {p[3]}\n💵 {p[4]} руб.\n🎫 Осталось: {p[5]}\n🆔 ID: {p[0]}"
            for p in performances
        )

        await update.message.reply_text(
            f"Доступные спектакли:\n\n{performances_msg}\n\nВведите ID спектакля для покупки:",
            reply_markup=ReplyKeyboardRemove()
        )
        return BUYING_TICKET

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
        return await start(update, context)


async def buy_ticket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text

        if not (performances := context.user_data.get('current_performances')):
            await update.message.reply_text("Сессия устарела. Начните заново /start")
            return ConversationHandler.END

        if text not in performances:
            await update.message.reply_text("Неверный ID. Введите корректный ID спектакля:")
            return BUYING_TICKET

        if buy_ticket(int(text)):
            await update.message.reply_text(
                "✅ Билет успешно куплен!\n"
                "Для нового поиска нажмите /start",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "❌ Билетов нет в наличии.\n"
                "Попробуйте другой спектакль (/start)",
                reply_markup=ReplyKeyboardRemove()
            )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Введите числовой ID спектакля:")
        return BUYING_TICKET
    except Exception as e:
        logger.error(f"Ошибка покупки: {e}")
        await update.message.reply_text("Ошибка при покупке. Попробуйте позже.")
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Действие отменено. Используйте /start для начала.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
