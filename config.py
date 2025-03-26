import os
import logging
import json  

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  
)
logger = logging.getLogger(__name__)

class NoGetUpdatesFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        return "getUpdates" not in message 

root_logger = logging.getLogger()

root_logger.addFilter(NoGetUpdatesFilter())

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'XXX')

RESULTS_FOLDER = "user_results"

QUESTION, RESULT, RATING, COMMENT = range(4)

OPTIONS_KEY = "options"
print("DEBUG: config.py - OPTIONS_KEY:", OPTIONS_KEY)

try:
    with open(os.path.join(os.path.dirname(__file__), 'data', 'specialties_data.json'), 'r', encoding='utf-8') as f:
        SPECIALTIES_DATA = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), 'data', 'questions.json'), 'r', encoding='utf-8') as f:
        QUESTIONS = json.load(f)
except FileNotFoundError:
    logger.critical("Файлы данных (specialties_data.json или questions.json) не найдены в папке 'data/'!")
    exit()
except json.JSONDecodeError:
    logger.critical("Ошибка декодирования JSON в файлах данных! Проверьте корректность JSON.")
    exit()

QUESTION_COUNT = len(QUESTIONS)