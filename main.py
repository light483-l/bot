import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN
from handlers import start, select_action, choose_theater, buy_ticket_handler, cancel
from database import init_db
from handlers import SELECTING_ACTION, CHOOSING_THEATER, BUYING_TICKET

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_action)],
            CHOOSING_THEATER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_theater)],
            BUYING_TICKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_ticket_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
