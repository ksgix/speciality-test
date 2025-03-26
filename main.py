import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN as TOKEN, QUESTION, RESULT, RATING, COMMENT  
from handlers import (
    start, start_test, ask_question, handle_answer,
    show_results, cancel
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    application = Application.builder().token(TOKEN).build()
   
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('test', start_test)],
        states={
            QUESTION: [CallbackQueryHandler(handle_answer)],
            RESULT: [CallbackQueryHandler(show_results)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
   
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(conv_handler)
   
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()