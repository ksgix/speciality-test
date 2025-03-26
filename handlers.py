import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.helpers import escape_markdown
from config import RESULTS_FOLDER, QUESTION_COUNT, QUESTIONS, SPECIALTIES_DATA, QUESTION, RESULT, OPTIONS_KEY
from utils import get_top_professions
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показываем информацию о боте и доступных командах."""
    info_text = (
        "👋 Привет!\n\n"
        "🤖 *О нашем боте для профориентации*\n\n"
        "Этот бот помогает определить подходящие для вас специальности на основе ваших предпочтений и способностей.\n\n"
        "📝 *О тесте*\n"
        f"• Тест состоит из {QUESTION_COUNT} вопросов\n"
        "• Время прохождения: около 10 минут\n"
        "• По результатам вы получите список наиболее подходящих специальностей\n\n"
        "📌 *Доступные команды*\n"
        "• /test - Начать тест профориентации\n"
        "• /cancel - Отменить текущий тест\n"
        "Чтобы начать тест, используйте команду /test."
    )
    await update.message.reply_markdown_v2(escape_markdown(info_text, version=2))


async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало теста."""
    logger.info(f"User {update.effective_user.id} started the test with /test command.")

    test_start_text = (
        f"Отлично 👍\n"
        f"Сейчас мы пройдем тест из {QUESTION_COUNT} вопросов, который поможет тебе "
        f"определиться с подходящими специальностями.\n\n"
        f"Выбирай ответы, которые лучше всего отражают твои предпочтения.\n"
        f"Начнем с первого вопроса."
    )
    await update.message.reply_markdown_v2(escape_markdown(test_start_text, version=2))

    context.user_data['question_number'] = 0
    context.user_data['answers'] = {}
    context.user_data['profession_scores'] = {}

    return await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Задаем вопрос."""
    question_number = context.user_data.get('question_number', 0)
    logger.info(f"Asking question {question_number + 1} to user {update.effective_user.id}.")

    if question_number >= QUESTION_COUNT:
        return await show_results(update, context)

    question_data = QUESTIONS[question_number]
    keyboard = [
        [InlineKeyboardButton(answer['text'], callback_data=f"{question_number}_{index}")]
        for index, answer in enumerate(question_data[OPTIONS_KEY])
    ]

    if question_number > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_{question_number}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    question_text = f"*Вопрос {question_number + 1} из {QUESTION_COUNT}*\n\n{question_data['question']}"

    if 'message_id' not in context.user_data:
        message = await update.message.reply_text(
            text=question_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        context.user_data['message_id'] = message.message_id
        context.user_data['chat_id'] = update.effective_chat.id
    else:
        await context.bot.edit_message_text(
            text=question_text,
            parse_mode='Markdown',
            chat_id=context.user_data['chat_id'],
            message_id=context.user_data['message_id'],
            reply_markup=reply_markup
        )

    return QUESTION

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатываем ответ пользователя."""
    query = update.callback_query
    await query.answer()  # Always acknowledge the query

    try:
        data_parts = query.data.split('_')
        if len(data_parts) != 2 and data_parts[0] != "back":
            raise ValueError(f"Invalid callback_data format: {query.data}")

        if data_parts[0] == "back":
            question_number = int(data_parts[1])
            context.user_data['question_number'] = question_number - 1

            if question_number - 1 in context.user_data['answers']:
                last_answer = context.user_data['answers'].pop(question_number - 1)
                if 'scores' in last_answer:
                    for specialty, score in last_answer['scores'].items():
                        if specialty in context.user_data['profession_scores']:
                            context.user_data['profession_scores'][specialty] -= score
                            if context.user_data['profession_scores'][specialty] <= 0:
                                context.user_data['profession_scores'].pop(specialty)

            return await ask_question(update, context)

        question_index, answer_index = map(int, data_parts)

        if question_index < 0 or question_index >= QUESTION_COUNT or answer_index < 0 or answer_index >= len(QUESTIONS[question_index]['options']):
            raise ValueError(f"Indices out of range: {question_index}, {answer_index}")

        answer_data = QUESTIONS[question_index]['options'][answer_index]
        context.user_data['answers'][question_index] = answer_data

        for specialty, score in answer_data.get('scores', {}).items():
            context.user_data['profession_scores'].setdefault(specialty, 0)
            context.user_data['profession_scores'][specialty] += score

        chosen_answer_text = answer_data['text']
        logger.info(f"User {update.effective_user.id} answered question {question_index + 1}: '{chosen_answer_text}'")

        context.user_data['question_number'] += 1

        if context.user_data['question_number'] < QUESTION_COUNT:
            return await ask_question(update, context)
        else:
            return await show_results(update, context, query)

    except Exception as e:
        logger.error(f"Error processing answer for user {update.effective_user.id}: {e}", exc_info=True)
        await query.edit_message_text(
            text="Произошла ошибка при обработке ответа. Пожалуйста, начните тест заново с помощью команды /test."
        )
        return ConversationHandler.END

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None) -> int:
    """Показываем результаты теста и сохраняем их."""
    logger.info(f"Showing test results to user {update.effective_user.id}.")
    try:
        profession_scores = context.user_data.get('profession_scores', {})

        if not profession_scores:
            message_text = "К сожалению, не удалось получить результаты теста. Пожалуйста, начните тест заново с помощью команды /test."
            if query:
                await query.edit_message_text(text=message_text)
            else:
                await update.message.reply_text(message_text)
            return ConversationHandler.END

        top_specialties_data = get_top_professions(profession_scores)
        context.user_data['top_specialties'] = top_specialties_data

        result_text = "📊 *Результаты теста*\n\n"
        result_text += "\n✨ *Рекомендованные специальности*:\n"

        if top_specialties_data:
            for i, spec_data in enumerate(top_specialties_data, 1):
                # CORRECTED LINE: Removed the ( and ) around the sphere
                result_text += f"{i}. *{spec_data['specialty']}*\n  {spec_data['description']}\n   Баллы: {spec_data['score']}\n\n"
        else:
            result_text += "К сожалению, не удалось подобрать подходящие специальности.\n"

        # Save results *before* sending the message, so even if sending fails, we have the data
        user_id = update.effective_user.id
        username = update.effective_user.username or "anonymous"

        result_data = {
            "user_id": user_id,
            "username": username,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "top_specialties": context.user_data.get('top_specialties', []),
            "profession_scores": context.user_data.get('profession_scores', {}),
        }

        file_path = os.path.join(RESULTS_FOLDER, f"result_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            save_success = True
            result_text += "Спасибо за прохождение теста!"  
        except Exception as e:
            logger.error(f"Error saving results for user {update.effective_user.id}: {e}", exc_info=True)
            save_success = False
            result_text += "Спасибо за прохождение теста!"  

        if query:
            await query.edit_message_text(
                text=result_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=result_text,
                parse_mode='Markdown'
            )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error showing results to user {update.effective_user.id}: {e}", exc_info=True)
        error_message = "Произошла ошибка при обработке результатов. Пожалуйста, начните тест заново с помощью команды /test."
        if query:
            await query.edit_message_text(text=error_message)
        else:
            await update.message.reply_text(error_message)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена теста."""
    logger.info(f"User {update.effective_user.id} cancelled the test with /cancel command.")
    await update.message.reply_text(
        "Тест профориентации отменен. Вы можете начать заново командой /test."
    )
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("test", start_test)],
    states={
        QUESTION: [CallbackQueryHandler(handle_answer)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)