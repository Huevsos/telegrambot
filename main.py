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
BOT_TOKEN = "8597427970:AAEU-5N1gWJe6Dow1AA6NPS82cGbHP0w5a4"  # Заменить на ваш токен!
ADMIN_GROUP_ID = -1003408636061   # ID группы для админов
PUBLIC_CHANNEL_ID = -5093355709   # ID канала для публики
ADMIN_ID = 7433757951  # Ваш личный ID Telegram

# ========== НАСТРОЙКИ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

# ========== КОМАНДЫ ==========
@dp.message(Command("getid"))
async def get_id_command(message: Message):
    chat_id = message.chat.id
    await message.answer(f"ID этого чата: `{chat_id}`", parse_mode="Markdown")

@dp.message(Command("setlimit"))
async def cmd_setlimit(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор.")
        return
    
    await state.set_state(AdminSetLimit.waiting_for_limit)
    await message.answer("Введите количество команд (1-20):")

@dp.message(AdminSetLimit.waiting_for_limit)
async def process_limit(message: Message, state: FSMContext):
    global MAX_TEAMS, registration_active, team_counter, teams_data
    
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 20:
            MAX_TEAMS = limit
            registration_active = True
            team_counter = 0
            teams_data = {}
            
            await message.answer(f"✅ Лимит: {MAX_TEAMS} команд\nРегистрация открыта!")
            
            if PUBLIC_CHANNEL_ID:
                await bot.send_message(
                    chat_id=PUBLIC_CHANNEL_ID,
                    text=f"🎮 Регистрация открыта!\nМаксимум: {MAX_TEAMS} команд\nИспользуйте /register"
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
    if message.from_user.id != ADMIN_ID:
        return
    
    global registration_active
    registration_active = False
    
    await message.answer("✅ Регистрация закрыта.")
    
    if PUBLIC_CHANNEL_ID:
        await bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text="⛔ Регистрация закрыта."
        )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    status_text = (
        f"📊 Статус:\n"
        f"• Лимит: {MAX_TEAMS}\n"
        f"• Зарегистрировано: {team_counter}\n"
        f"• Свободно: {MAX_TEAMS - team_counter}\n"
        f"• Статус: {'✅ Открыта' if registration_active else '❌ Закрыта'}\n"
    )
    
    if teams_data:
        status_text += "\nКоманды:\n"
        for num, team in teams_data.items():
            status_text += f"#{num}: {team['name']}\n"
    
    await message.answer(status_text)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not registration_active:
        await message.answer("⏳ Регистрация пока не открыта.")
        return
    
    await message.answer(
        f"👋 Добро пожаловать!\nОсталось мест: {MAX_TEAMS - team_counter}\n"
        "Для регистрации команды используйте /register"
    )

@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    if not registration_active:
        await message.answer("❌ Регистрация закрыта.")
        return
    
    if team_counter >= MAX_TEAMS:
        await message.answer("❌ Все места заняты!")
        return
    
    if message.chat.type != "private":
        await message.answer("⚠️ Регистрация только в личных сообщениях.")
        return
    
    await state.set_state(TeamRegistration.waiting_for_team_name)
    await message.answer("📝 Введите название команды:")

@dp.message(TeamRegistration.waiting_for_team_name)
async def process_team_name(message: Message, state: FSMContext):
    team_name = message.text.strip()[:50]
    await state.update_data(team_name=team_name)
    await state.set_state(TeamRegistration.waiting_for_team_avatar)
    await message.answer(f"✅ Название: {team_name}\n\n📸 Отправьте аватарку (фото):")

@dp.message(TeamRegistration.waiting_for_team_avatar, F.photo)
async def process_team_avatar(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(avatar_file_id=photo.file_id)
    await state.set_state(TeamRegistration.waiting_for_players)
    await message.answer(
        "✅ Аватарка принята!\n\n"
        "👥 Введите данные игроков:\n"
        "ID_игрока1 Ник1\nID_игрока2 Ник2\n\n"
        "Пример:\n123456789 PlayerOne\n987654321 PlayerTwo"
    )

@dp.message(TeamRegistration.waiting_for_team_avatar)
async def wrong_avatar(message: Message):
    await message.answer("❌ Отправьте фото.")

@dp.message(TeamRegistration.waiting_for_players)
async def process_players(message: Message, state: FSMContext):
    global team_counter
    
    if team_counter >= MAX_TEAMS:
        await message.answer("❌ Все места уже заняты!")
        await state.clear()
        return
    
    players = []
    for line in message.text.strip().split('\n')[:10]:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].isdigit():
            players.append({
                'id': parts[0],
                'nickname': ' '.join(parts[1:])[:50]
            })
    
    if not players:
        await message.answer("❌ Неверный формат.")
        return
    
    data = await state.get_data()
    team_name = data.get('team_name')
    avatar_file_id = data.get('avatar_file_id')
    
    team_number = team_counter + 1
    teams_data[team_number] = {
        'name': team_name,
        'avatar': avatar_file_id,
        'players': players,
        'captain': f"@{message.from_user.username}" if message.from_user.username else "Без username"
    }
    
    # В канал
    if PUBLIC_CHANNEL_ID:
        try:
            await bot.send_photo(
                chat_id=PUBLIC_CHANNEL_ID,
                photo=avatar_file_id,
                caption=f"🏆 Команда #{team_number}: {team_name}"
            )
        except:
            pass
    
    # Админам
    if ADMIN_GROUP_ID:
        players_text = "\n".join([f"ID: {p['id']} | Ник: {p['nickname']}" for p in players])
        admin_msg = f"🔒 Команда #{team_number}: {team_name}\nСостав:\n{players_text}"
        try:
            await bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_msg)
        except:
            pass
    
    team_counter += 1
    remaining = MAX_TEAMS - team_counter
    
    await message.answer(
        f"✅ Команда зарегистрирована!\n"
        f"Номер: #{team_number}\n"
        f"Осталось мест: {remaining}"
    )
    
    if team_counter >= MAX_TEAMS:
        global registration_active
        registration_active = False
        if PUBLIC_CHANNEL_ID:
            await bot.send_message(
                chat_id=PUBLIC_CHANNEL_ID,
                text="🎯 Регистрация завершена! Все места заняты."
            )
    
    await state.clear()

@dp.message(Command("teams"))
async def cmd_teams(message: Message):
    if not teams_data:
        await message.answer("📭 Нет команд.")
        return
    
    text = f"Команды ({team_counter}/{MAX_TEAMS}):\n\n"
    for num, team in teams_data.items():
        text += f"#{num}: {team['name']}\n"
    
    await message.answer(text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📋 Команды:\n"
        "/start - Начать\n"
        "/register - Регистрация команды\n"
        "/teams - Список команд\n"
        "/help - Помощь\n"
        "/getid - Получить ID чата"
    )
    
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "\n\n👑 Админ:\n"
            "/setlimit - Установить лимит\n"
            "/closereg - Закрыть регистрацию\n"
            "/status - Статус"
        )
    
    await message.answer(help_text)

@dp.message()
async def handle_other(message: Message):
    await message.answer("Неизвестная команда. Используйте /help")

async def main():
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
if __name__ == "__main__":
    asyncio.run(main())
