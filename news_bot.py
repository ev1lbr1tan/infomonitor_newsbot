import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from news_collector import NewsCollector

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InfoMonitor:
    """Основной класс Telegram бота ИнфоМонитор"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.news_collector = NewsCollector()
        self.scheduler = AsyncIOScheduler()
        self.user_news_state = {}  # {user_id: {'news_list': [...], 'current_index': 0}}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_text = """
🤖 *Добро пожаловать в ИнфоМонитор!*

Я буду присылать вам актуальные новости каждый день в 9:00 утра (MSK).

📰 *Доступные команды:*
• /news - получить новости прямо сейчас
• /help - справка по командам

📊 Источники новостей:
• РИА Новости
• ТАСС
• Лента.ру
• Ведомости
• РБК
• Коммерсантъ
• Известия
• Газета.ру
• RT
• Интерфакс

Бот работает 24/7 и автоматически собирает последние новости!
        """

        # Создаем постоянную клавиатуру с кнопкой для получения новостей
        keyboard = [[KeyboardButton("📰 Получить новости")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
🔧 *Справка по командам ИнфоМонитора*

📰 *Основные команды:*
• `/news` - получить последние новости
• `/start` - начать работу с ботом
• `/help` - показать эту справку

⏰ *Автоматическая рассылка:*
Новости приходят каждый день в 9:00 утра (MSK)

📊 *Источники новостей:*
• РИА Новости
• ТАСС
• Лента.ру
• Ведомости
• РБК
• Коммерсантъ
• Известия
• Газета.ру
• RT
• Интерфакс
        """

        # Создаем постоянную клавиатуру с кнопкой для получения новостей
        keyboard = [[KeyboardButton("📰 Получить новости")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /news - получение новостей по запросу"""
        user_id = update.effective_user.id
        await update.message.reply_text("📡 Собираю последние новости...")

        try:
            news_list = self.news_collector.get_latest_news(limit=10)
            if not news_list:
                await update.message.reply_text("😔 К сожалению, не удалось получить новости. Попробуйте позже.")
                return

            # Сохраняем состояние новостей для пользователя
            self.user_news_state[user_id] = {
                'news_list': news_list,
                'current_index': 0
            }

            # Показываем первую новость с клавиатурой
            await self.show_news(update, user_id)

        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            await update.message.reply_text("😔 Произошла ошибка при получении новостей. Попробуйте позже.")

    async def show_news(self, update: Update, user_id: int, edit_message=False):
        """Показать текущую новость с клавиатурой навигации"""
        if user_id not in self.user_news_state:
            if edit_message:
                await update.callback_query.edit_message_text("😔 Новости не найдены. Используйте /news для получения новостей.")
            else:
                await update.message.reply_text("😔 Новости не найдены. Используйте /news для получения новостей.")
            return

        state = self.user_news_state[user_id]
        news_list = state['news_list']
        current_index = state['current_index']

        if current_index >= len(news_list):
            if edit_message:
                await update.callback_query.edit_message_text("😔 Больше новостей нет.")
            else:
                await update.message.reply_text("😔 Больше новостей нет.")
            return

        news = news_list[current_index]
        message = self.news_collector.format_single_news(news, current_index, len(news_list))

        # Создаем inline клавиатуру
        keyboard = []
        if current_index > 0:
            keyboard.append(InlineKeyboardButton("⬅️ Прошлая новость", callback_data="prev_news"))
        if current_index < len(news_list) - 1:
            keyboard.append(InlineKeyboardButton("Следующая новость ➡️", callback_data="next_news"))

        reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

        if edit_message:
            await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)
        else:
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup, disable_web_page_preview=True)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов от inline клавиатуры"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if user_id not in self.user_news_state:
            await query.edit_message_text("😔 Сессия новостей истекла. Используйте /news для получения свежих новостей.")
            return

        state = self.user_news_state[user_id]
        current_index = state['current_index']

        if data == "next_news":
            state['current_index'] = min(current_index + 1, len(state['news_list']) - 1)
        elif data == "prev_news":
            state['current_index'] = max(current_index - 1, 0)

        # Обновляем сообщение с новой новостью
        await self.show_news(update, user_id, edit_message=True)

    async def daily_news_job(self):
        """Задача для ежедневной отправки новостей"""
        try:
            # Получаем всех пользователей, которые запустили бота
            # В реальном приложении здесь должна быть база данных
            logger.info("Отправка ежедневных новостей...")
            
            news_list = self.news_collector.get_latest_news(limit=5)
            message = self.news_collector.format_news_message(news_list)
            message = f"🌅 *Доброе утро! ИнфоМонитор приносит свежие новости:*\n\n" + message
            
            # Здесь должен быть код для отправки всем подписчикам
            # Для демонстрации просто логируем
            logger.info(f"Подготовлено сообщение с {len(news_list)} новостями")
            
        except Exception as e:
            logger.error(f"Ошибка при ежедневной отправке новостей: {e}")
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user_message = update.message.text.lower()

        if user_message == "📰 получить новости":
            await self.news_command(update, context)
        elif any(word in user_message for word in ['новости', 'news', 'что нового']):
            await self.news_command(update, context)
        elif any(word in user_message for word in ['помощь', 'help', 'справка']):
            await self.help_command(update, context)
        else:
            response = """
🤖 Я ИнфоМонитор!

Используйте кнопку ниже или команду `/news` для получения новостей.
            """
            await update.message.reply_text(response, parse_mode='Markdown')
            
    def setup_scheduler(self):
        """Настройка планировщика для ежедневной отправки новостей"""
        # Запускаем ежедневно в 9:00 MSK (6:00 UTC)
        self.scheduler.add_job(
            self.daily_news_job,
            CronTrigger(hour=6, minute=0),  # 9:00 MSK = 6:00 UTC
            id='daily_news'
        )
        
    def run(self):
        """Запуск бота"""
        # Создаем приложение
        application = Application.builder().token(self.bot_token).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("news", self.news_command))

        # Добавляем обработчик callback запросов
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Добавляем обработчик сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Настраиваем планировщик
        self.setup_scheduler()
        self.scheduler.start()
        
        logger.info("🤖 Бот запущен...")
        logger.info("📅 Ежедневная рассылка новостей настроена на 9:00 MSK")
        
        # Запускаем бота
        application.run_polling()

def main():
    """Главная функция"""
    # Получаем токен бота из переменных окружения
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not BOT_TOKEN:
        print("❌ Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        print("💡 Создайте бота через @BotFather и получите токен")
        return
        
    # Создаем и запускаем бота
    bot = InfoMonitor(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()