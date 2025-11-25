import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
import datetime
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем настройки из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID', '@cosinxx_prime')
ADMIN_IDS = [7433757951]

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен!")
    exit(1)

# База данных
class ContestDB:
    def __init__(self):
        self.conn = sqlite3.connect('contests.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                channel_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                winners_count INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contest_id) REFERENCES contests (id)
            )
        ''')
        self.conn.commit()

    def add_contest(self, name, description, end_time, winners_count=1, channel_message_id=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO contests (name, description, end_time, winners_count, channel_message_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, end_time, winners_count, channel_message_id))
        self.conn.commit()
        return cursor.lastrowid

    def get_active_contests(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM contests 
            WHERE is_active = TRUE AND end_time > datetime('now')
        ''')
        return cursor.fetchall()

    def get_contest(self, contest_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM contests WHERE id = ?', (contest_id,))
        return cursor.fetchone()

    def end_contest(self, contest_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE contests SET is_active = FALSE WHERE id = ?', (contest_id,))
        self.conn.commit()

    def add_participant(self, contest_id, user_id, username, full_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id FROM participants 
            WHERE contest_id = ? AND user_id = ?
        ''', (contest_id, user_id))
        if cursor.fetchone() is None:
            cursor.execute('''
                INSERT INTO participants (contest_id, user_id, username, full_name)
                VALUES (?, ?, ?, ?)
            ''', (contest_id, user_id, username, full_name))
            self.conn.commit()
            return True
        return False

    def get_participants_count(self, contest_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM participants WHERE contest_id = ?
        ''', (contest_id,))
        return cursor.fetchone()[0]

    def get_random_winners(self, contest_id, count):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM participants 
            WHERE contest_id = ? 
            ORDER BY RANDOM() 
            LIMIT ?
        ''', (contest_id, count))
        return cursor.fetchall()

db = ContestDB()

class ContestBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        self.channel_id = CHANNEL_ID

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("create", self.create_contest))
        self.application.add_handler(CommandHandler("contests", self.show_active_contests))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if context.args and context.args[0].startswith('participate'):
            try:
                contest_id = int(context.args[0].split('_')[1]) if '_' in context.args[0] else None
                if contest_id:
                    await self.handle_participation_start(update, context, contest_id, user)
                    return
            except (ValueError, IndexError):
                pass
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я бот для проведения конкурсов в канале.\n"
            "Для участия в конкурсе нажмите кнопку 'Участвовать' под постом с конкурсом в канале."
        )

    async def handle_participation_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, contest_id: int, user):
        contest = db.get_contest(contest_id)
        if not contest:
            await update.message.reply_text("❌ Конкурс не найден!")
            return

        if not contest[6]:
            await update.message.reply_text("❌ Этот конкурс уже завершен!")
            return

        if db.add_participant(contest_id, user.id, user.username, user.full_name):
            participants_count = db.get_participants_count(contest_id)
            await self.update_contest_message(contest_id)
            
            end_time = datetime.datetime.fromisoformat(contest[5])
            time_left = end_time - datetime.datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
            
            await update.message.reply_text(
                f"✅ {user.first_name}, вы участвуете в конкурсе!\n\n"
                f"🎯 **{contest[1]}**\n"
                f"👥 Участников: {participants_count}\n"
                f"⏰ Завершится через: {hours_left}ч {minutes_left}м"
            )
        else:
            await update.message.reply_text(f"ℹ️ Вы уже участвуете в этом конкурсе!")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not await self.is_admin(user):
            await update.message.reply_text("❌ Нет прав администратора!")
            return

        keyboard = [
            [InlineKeyboardButton("🎯 Создать конкурс", callback_data="create_contest_menu")],
            [InlineKeyboardButton("📊 Активные конкурсы", callback_data="active_contests")],
            [InlineKeyboardButton("⏰ Конкурс (1 час)", callback_data="quick_1h")],
            [InlineKeyboardButton("⏰ Конкурс (3 часа)", callback_data="quick_3h")],
            [InlineKeyboardButton("⏰ Конкурс (6 часов)", callback_data="quick_6h")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("👨‍💻 Панель администратора:", reply_markup=reply_markup)

    async def create_contest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not await self.is_admin(user):
            await update.message.reply_text("❌ Нет прав администратора!")
            return

        if context.args:
            try:
                contest_data = ' '.join(context.args)
                parts = contest_data.split('|')
                
                if len(parts) < 4:
                    await update.message.reply_text("❌ Формат: /create Название|Описание|Часы|Победители")
                    return

                name = parts[0].strip()
                description = parts[1].strip()
                hours = int(parts[2].strip())
                winners_count = int(parts[3].strip())

                end_time = datetime.datetime.now() + datetime.timedelta(hours=hours)
                channel_message_id = await self.create_contest_post(context, name, description, end_time, winners_count)
                contest_id = db.add_contest(name, description, end_time, winners_count, channel_message_id)
                self.schedule_contest_end(contest_id, hours)
                
                await update.message.reply_text(f"✅ Конкурс создан! ID: {contest_id}")

            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        else:
            await update.message.reply_text("📝 Формат: /create Название|Описание|Часы|Победители")

    async def create_contest_post(self, context: ContextTypes.DEFAULT_TYPE, name: str, description: str, end_time: datetime.datetime, winners_count: int):
        try:
            bot_username = (await context.bot.get_me()).username
            keyboard = [
                [InlineKeyboardButton("🎯 Участвовать", url=f"https://t.me/{bot_username}?start=test")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            time_left = end_time - datetime.datetime.now()
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)

            message_text = (
                f"🎉 **КОНКУРС!** 🎉\n\n"
                f"**{name}**\n\n"
                f"{description}\n\n"
                f"⏰ **Завершится через:** {hours_left}ч {minutes_left}м\n"
                f"🏆 **Победителей:** {winners_count}\n"
                f"👥 **Участников:** 0\n\n"
                f"**Для участия нажмите кнопку:** 👇"
            )

            message = await context.bot.send_message(
                chat_id=self.channel_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return message.message_id
            
        except Exception as e:
            logger.error(f"Ошибка при создании поста в канале: {e}")
            raise e

    async def update_contest_message(self, contest_id: int):
        try:
            contest = db.get_contest(contest_id)
            if not contest or not contest[6]:
                return

            if not contest[3]:
                return

            participants_count = db.get_participants_count(contest_id)
            time_left = datetime.datetime.fromisoformat(contest[5]) - datetime.datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))

            message_text = (
                f"🎉 **КОНКУРС!** 🎉\n\n"
                f"**{contest[1]}**\n\n"
                f"{contest[2]}\n\n"
                f"⏰ **Конкурс закончится через:** {hours_left}ч {minutes_left}м\n"
                f"🏆 **Количество победителей:** {contest[7]}\n"
                f"👥 **Участников:** {participants_count}\n\n"
                f"**Для участия нажмите кнопку ниже:** 👇"
            )

            bot_username = (await self.application.bot.get_me()).username
            keyboard = [
                [InlineKeyboardButton("🎯 Участвовать в конкурсе", url=f"https://t.me/{bot_username}?start=participate_{contest_id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.application.bot.edit_message_text(
                chat_id=self.channel_id,
                message_id=contest[3],
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения конкурса {contest_id}: {e}")

    def schedule_contest_end(self, contest_id: int, hours: int):
        async def end_contest_auto():
            await asyncio.sleep(hours * 3600)
            await self.auto_end_contest(contest_id)
        
        asyncio.create_task(end_contest_auto())

    async def auto_end_contest(self, contest_id: int):
        contest = db.get_contest(contest_id)
        if not contest or not contest[6]:
            return

        participants = db.get_participants(contest_id)
        if participants:
            winners = db.get_random_winners(contest_id, contest[7])
            
            winners_text = "🏆 **КОНКУРС ЗАВЕРШЕН!** 🏆\n\n"
            winners_text += f"**Конкурс:** {contest[1]}\n\n"
            winners_text += "**Победители:**\n"
            
            for i, winner in enumerate(winners, 1):
                _, _, user_id, username, full_name, _ = winner
                user_mention = f"@{username}" if username else full_name
                winners_text += f"{i}. {user_mention}\n"
            
            winners_text += f"\n🎉 Поздравляем победителей!"
        else:
            winners_text = f"📭 Конкурс '{contest[1]}' завершен.\nУчастников не было."

        try:
            await self.application.bot.send_message(
                chat_id=self.channel_id,
                text=winners_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при публикации результатов: {e}")

        db.end_contest(contest_id)

    async def show_active_contests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not await self.is_admin(user):
            await update.message.reply_text("❌ Нет прав администратора!")
            return

        contests = db.get_active_contests()
        if not contests:
            await update.message.reply_text("📭 Активных конкурсов нет.")
            return

        text = "📊 **Активные конкурсы:**\n\n"
        
        for contest in contests:
            contest_id, name, description, channel_msg_id, created_at, end_time, is_active, winners_count = contest
            time_left = datetime.datetime.fromisoformat(end_time) - datetime.datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
            
            text += f"🎯 **{name}** (ID: {contest_id})\n"
            text += f"⏰ Осталось: {hours_left}ч {minutes_left}м\n"
            text += f"👥 Участников: {db.get_participants_count(contest_id)}\n"
            text += f"🏆 Победителей: {winners_count}\n"
            text += "────────────────────\n\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        user = query.from_user

        if data.startswith("participate_"):
            contest_id = int(data.split("_")[1])
            await self.handle_participation_button(query, contest_id, user)
            
        elif data == "create_contest_menu":
            await query.edit_message_text("📝 Используйте: /create Название|Описание|Часы|Победители")
            
        elif data == "active_contests":
            await self.show_active_contests_callback(query)
            
        elif data.startswith("quick_"):
            hours_map = {"1h": 1, "3h": 3, "6h": 6}
            hours = hours_map[data.split("_")[1]]
            await self.create_quick_contest(query, hours)
            
        elif data.startswith("end_"):
            contest_id = int(data.split("_")[1])
            await self.end_contest_handler(query, contest_id)

    async def create_quick_contest(self, query, hours: int):
        name = f"Быстрый конкурс ({hours}ч)"
        description = f"Участвуйте в конкурсе и выигрывайте призы! Конкурс продлится {hours} часов."
        winners_count = 1
        
        end_time = datetime.datetime.now() + datetime.timedelta(hours=hours)
        channel_message_id = await self.create_contest_post(self.application, name, description, end_time, winners_count)
        contest_id = db.add_contest(name, description, end_time, winners_count, channel_message_id)
        await self.update_contest_message(contest_id)
        self.schedule_contest_end(contest_id, hours)
        
        await query.edit_message_text(f"✅ Конкурс создан! ID: {contest_id}")

    async def handle_participation_button(self, query, contest_id: int, user):
        contest = db.get_contest(contest_id)
        if not contest:
            await query.edit_message_text("❌ Конкурс не найден!")
            return

        if not contest[6]:
            await query.edit_message_text("❌ Этот конкурс уже завершен!")
            return

        if db.add_participant(contest_id, user.id, user.username, user.full_name):
            participants_count = db.get_participants_count(contest_id)
            await self.update_contest_message(contest_id)
            
            await query.edit_message_text(
                f"✅ {user.first_name}, вы участвуете в конкурсе!\n\n"
                f"🎯 **{contest[1]}**\n"
                f"👥 Участников: {participants_count}"
            )
        else:
            await query.edit_message_text(f"ℹ️ Вы уже участвуете в этом конкурсе!")

    async def show_active_contests_callback(self, query):
        contests = db.get_active_contests()
        if not contests:
            await query.edit_message_text("📭 Активных конкурсов нет.")
            return

        text = "📊 **Активные конкурсы:**\n\n"
        keyboard = []
        
        for contest in contests:
            contest_id, name, description, channel_msg_id, created_at, end_time, is_active, winners_count = contest
            time_left = datetime.datetime.fromisoformat(end_time) - datetime.datetime.now()
            hours_left = max(0, int(time_left.total_seconds() // 3600))
            minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
            
            text += f"🎯 **{name}** (ID: {contest_id})\n"
            text += f"⏰ Осталось: {hours_left}ч {minutes_left}м\n"
            text += f"👥 Участников: {db.get_participants_count(contest_id)}\n"
            text += f"🏆 Победителей: {winners_count}\n"
            text += "────────────────────\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"Завершить '{name}'", 
                callback_data=f"end_{contest_id}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def end_contest_handler(self, query, contest_id: int):
        contest = db.get_contest(contest_id)
        if not contest:
            await query.edit_message_text("❌ Конкурс не найден!")
            return

        participants = db.get_participants(contest_id)
        if participants:
            winners = db.get_random_winners(contest_id, contest[7])
            
            winners_text = "🏆 **КОНКУРС ЗАВЕРШЕН!** 🏆\n\n"
            winners_text += f"**Конкурс:** {contest[1]}\n\n"
            winners_text += "**Победители:**\n"
            
            for i, winner in enumerate(winners, 1):
                _, _, user_id, username, full_name, _ = winner
                user_mention = f"@{username}" if username else full_name
                winners_text += f"{i}. {user_mention}\n"
        else:
            winners_text = f"📭 Конкурс '{contest[1]}' завершен.\nУчастников не было."

        try:
            await query.bot.send_message(
                chat_id=self.channel_id,
                text=winners_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при публикации результатов: {e}")

        db.end_contest(contest_id)
        await query.edit_message_text(f"✅ Конкурс завершен! Участников: {len(participants)}")

    async def is_admin(self, user):
        return user.id in ADMIN_IDS

    def run(self):
        logger.info("🚀 Бот запускается на Railway...")
        self.application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = ContestBot(BOT_TOKEN)
    bot.run()
