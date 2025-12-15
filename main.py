import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

# ========== ВАШИ ДАННЫЕ ==========
# Вставьте сюда свои данные:

BOT_TOKEN = "8597427970:AAEU-5N1gWJe6Dow1AA6NPS82cGbHP0w5a4"  # Получить у @BotFather
ADMIN_GROUP_ID = -1003408636061  # ID группы для админов (с минусом)
PUBLIC_CHANNEL_ID = -5093355709  # ID канала для публики (с минусом)
ADMIN_ID = 7433757951  # Ваш личный ID Telegram

# ========== НАСТРОЙКИ ==========

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранение данных
teams_data = {}
team_counter = 0
MAX_TEAMS = 0
registration_active = False

# Состояния
class TeamRegistration(StatesGroup):
    waiting_for_team_name = State()
    waiting_for_team_avatar = State()
    waiting_for_players = State()

class AdminSetLimit(StatesGroup):
    waiting_for_limit = State()

# ========== КОМАНДА ДЛЯ ПОЛУЧЕНИЯ ID ==========
@dp.message(Command("getid"))
async def get_id_command(message: Message):
    """Получить ID чата"""
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = message.chat.title or "Личные сообщения"
    
    response = (
        f"📊 Информация о чате:\n"
        f"• Тип: {chat_type}\n"
        f"• Название: {chat_title}\n"
        f"• ID: `{chat_id}`\n\n"
        f"🔹 Обычные группы: ID без минуса\n"
        f"🔹 Супергруппы/каналы: ID начинается с `-100`"
    )
    
    await message.answer(response, parse_mode="Markdown")

# ========== АДМИН КОМАНДЫ ==========

@dp.message(Command("setlimit"))
async def cmd_setlimit(message: Message, state: FSMContext):
    """Установить лимит команд (только админ)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может устанавливать лимит.")
        return
    
    await state.set_state(AdminSetLimit.waiting_for_limit)
    await message.answer("Введите количество команд для регистрации (1-20):")

@dp.message(AdminSetLimit.waiting_for_limit)
async def process_limit(message: Message, state: FSMContext):
    """Обработка лимита от админа"""
    global MAX_TEAMS, registration_active, team_counter, teams_data
    
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 20:
            MAX_TEAMS = limit
            registration_active = True
            team_counter = 0
            teams_data = {}
            
            await message.answer(
                f"✅ Лимит установлен: {MAX_TEAMS} команд\n"
                f"Регистрация открыта! Отправьте команду /register для участия."
            )
            
            # Уведомление в канал
            if PUBLIC_CHANNEL_ID:
                await bot.send_message(
                    chat_id=PUBLIC_CHANNEL_ID,
                    text=f"🎮 Регистрация команд открыта!\nМаксимум команд: {MAX_TEAMS}\n\nИспользуйте /register для участия."
                )
        else:
            await message.answer("Введите число от 1 до 20:")
            return
    except ValueError:
        await message.answer("Введите число от 1 до 20:")
        return
    
    await state.clear()

@dp.message(Command("closereg"))
async def cmd_closereg(message: Message):
    """Закрыть регистрацию (только админ)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может закрывать регистрацию.")
        return
    
    global registration_active
    registration_active = False
    
    await message.answer("✅ Регистрация закрыта.")
    
    if PUBLIC_CHANNEL_ID:
        await bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text="⛔ Регистрация команд закрыта."
        )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Показать статус регистрации (только админ)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может просматривать статус.")
        return
    
    status_text = (
        f"📊 Статус регистрации:\n"
        f"• Лимит команд: {MAX_TEAMS}\n"
        f"• Зарегистрировано: {team_counter}\n"
        f"• Свободных мест: {MAX_TEAMS - team_counter}\n"
        f"• Регистрация: {'✅ Открыта' if registration_active else '❌ Закрыта'}\n\n"
    )
    
    if teams_data:
        status_text += "Зарегистрированные команды:\n"
        for num, team in teams_data.items():
            status_text += f"#{num}: {team['name']} ({len(team['players'])} игроков)\n"
    
    await message.answer(status_text)

# ========== КОМАНДЫ ДЛЯ ВСЕХ ==========

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Начало работы"""
    if not registration_active:
        await message.answer("⏳ Регистрация команд пока не открыта. Ожидайте объявления.")
        return
    
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        f"Регистрация команд открыта! Осталось мест: {MAX_TEAMS - team_counter}\n"
        "Для регистрации команды используйте /register"
    )

@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    """Начать регистрацию команды"""
    # Проверка активности регистрации
    if not registration_active:
        await message.answer("❌ Регистрация закрыта.")
        return
    
    # Проверка лимита
    if team_counter >= MAX_TEAMS:
        await message.answer("❌ Все места заняты! Регистрация завершена.")
        return
    
    # Только личные сообщения
    if message.chat.type != "private":
        await message.answer("⚠️ Регистрация только в личных сообщениях с ботом.")
        return
    
    await state.set_state(TeamRegistration.waiting_for_team_name)
    await message.answer("📝 Введите название команды:")

@dp.message(TeamRegistration.waiting_for_team_name)
async def process_team_name(message: Message, state: FSMContext):
    """Получение названия команды"""
    team_name = message.text.strip()[:50]
    await state.update_data(team_name=team_name)
    await state.set_state(TeamRegistration.waiting_for_team_avatar)
    await message.answer(f"✅ Название: {team_name}\n\n📸 Отправьте аватарку команды (фото):")

@dp.message(TeamRegistration.waiting_for_team_avatar, F.photo)
async def process_team_avatar(message: Message, state: FSMContext):
    """Получение аватарки команды"""
    photo = message.photo[-1]
    await state.update_data(avatar_file_id=photo.file_id)
    await state.set_state(TeamRegistration.waiting_for_players)
    await message.answer(
        "✅ Аватарка принята!\n\n"
        "👥 Введите данные игроков:\n"
        "<code>ID_игрока1 Ник1\nID_игрока2 Ник2</code>\n\n"
        "Пример:\n<code>123456789 PlayerOne\n987654321 PlayerTwo</code>"
    )

@dp.message(TeamRegistration.waiting_for_team_avatar)
async def wrong_avatar(message: Message):
    """Ошибка: не фото"""
    await message.answer("❌ Отправьте фото (аватарку команды).")

@dp.message(TeamRegistration.waiting_for_players)
async def process_players(message: Message, state: FSMContext):
    """Получение данных игроков и завершение регистрации"""
    global team_counter
    
    # Проверяем, не заняты ли уже все места
    if team_counter >= MAX_TEAMS:
        await message.answer("❌ К сожалению, все места уже заняты!")
        await state.clear()
        return
    
    # Парсим игроков
    players = []
    for line in message.text.strip().split('\n')[:10]:  # максимум 10 игроков
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].isdigit():
            players.append({
                'id': parts[0],
                'nickname': ' '.join(parts[1:])[:50]
            })
    
    if not players:
        await message.answer("❌ Неверный формат. Введите снова:")
        return
    
    # Получаем сохраненные данные
    data = await state.get_data()
    team_name = data.get('team_name')
    avatar_file_id = data.get('avatar_file_id')
    
    # Сохраняем команду
    team_number = team_counter + 1
    teams_data[team_number] = {
        'name': team_name,
        'avatar': avatar_file_id,
        'players': players,
        'captain': f"@{message.from_user.username}" if message.from_user.username else "Без username"
    }
    
    # Публичное сообщение в канал (только название и аватарка)
    if PUBLIC_CHANNEL_ID:
        try:
            await bot.send_photo(
                chat_id=PUBLIC_CHANNEL_ID,
                photo=avatar_file_id,
                caption=f"🏆 Команда #{team_number}: {team_name}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")
    
    # Приватное сообщение админам (все данные)
    if ADMIN_GROUP_ID:
        players_text = "\n".join([f"ID: {p['id']} | Ник: {p['nickname']}" for p in players])
        admin_msg = (
            f"🔒 ПРИВАТНЫЕ ДАННЫЕ\n\n"
            f"Команда #{team_number}: {team_name}\n"
            f"Капитан: {teams_data[team_number]['captain']}\n\n"
            f"📋 Состав команды:\n{players_text}\n\n"
            f"Всего игроков: {len(players)}"
        )
        try:
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=admin_msg
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админам: {e}")
    
    # Ответ пользователю
    team_counter += 1
    remaining = MAX_TEAMS - team_counter
    
    await message.answer(
        f"✅ Команда {team_name} успешно зарегистрирована!\n\n"
        f"Номер команды: #{team_number}\n"
        f"Количество игроков: {len(players)}\n"
        f"Осталось мест: {remaining}"
    )
    
    # Проверка заполнения всех мест
    if team_counter >= MAX_TEAMS:
        global registration_active
        registration_active = False
        
        # Уведомление в канал о завершении регистрации
        if PUBLIC_CHANNEL_ID:
            await bot.send_message(
                chat_id=PUBLIC_CHANNEL_ID,
                text="🎯 Регистрация завершена! Все места заняты."
            )
    
    await state.clear()

@dp.message(Command("teams"))
async def cmd_teams(message: Message):
    """Показать список зарегистрированных команд"""
    if not teams_data:
        await message.answer("📭 Нет зарегистрированных команд.")
        return
    
    text = f"📋 Зарегистрированные команды ({team_counter}/{MAX_TEAMS}):\n\n"
    for num, team in teams_data.items():
        text += f"#{num}: {team['name']} ({len(team['players'])} игроков)\n"
    
    await message.answer(text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку"""
    help_text = (
        "🤖 <b>Бот регистрации команд</b>\n\n"
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/register - Регистрация новой команды\n"
        "/teams - Просмотр зарегистрированных команд\n"
        "/help - Справка\n"
        "/getid - Получить ID чата (для настройки)\n\n"
    )
    
    # Добавляем команды админа
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "<b>👑 Команды администратора:</b>\n"
            "/setlimit - Установить лимит команд\n"
            "/closereg - Закрыть регистрацию\n"
            "/status - Показать статус регистрации\n\n"
        )
    
    help_text += (
        "<b>Процесс регистрации:</b>\n"
        "1. Название команды\n"
        "2. Аватарка (логотип)\n"
        "3. Данные игроков (ID и никнеймы)"
    )
    
    await message.answer(help_text)

# ========== ЗАПУСК БОТА ==========

async def main():
    """Запуск бота"""
    logger.info("=" * 50)
    logger.info("Бот запущен!")
    logger.info(f"ID администратора: {ADMIN_ID}")
    logger.info(f"ID канала: {PUBLIC_CHANNEL_ID}")
    logger.info(f"ID группы админов: {ADMIN_GROUP_ID}")
    logger.info("=" * 50)
    
    # Отправляем сообщение админу о запуске
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="🤖 Бот запущен!\n\n"
                 "Для начала регистрации используйте команду /setlimit"
        )
    except:
        logger.warning("Не удалось отправить сообщение администратору")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
