import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import asyncio

# ========== ВАШИ ДАННЫЕ ==========
BOT_TOKEN = "8597427970:AAEU-5N1gWJe6Dow1AA6NPS82cGbHP0w5a4"  # Замените на ваш токен!
ADMIN_GROUP_ID = -5093355709  # Группа для админов
PUBLIC_CHANNEL_ID = -1003408636061  # ⚠️ Замените на ваш ID канала (должен начинаться с -100)
ADMIN_ID = 7433757951  # Ваш личный ID

# ========== НАСТРОЙКИ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
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

# ========== КОМАНДЫ ДЛЯ ПРОВЕРКИ ==========
@dp.message(Command("testchannel"))
async def test_channel_command(message: Message):
    """Проверить отправку в канал"""
    if PUBLIC_CHANNEL_ID:
        try:
            await bot.send_message(
                chat_id=PUBLIC_CHANNEL_ID,
                text="✅ Тестовое сообщение из бота! Канал работает."
            )
            await message.answer(f"✅ Сообщение отправлено в канал ID: {PUBLIC_CHANNEL_ID}")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("checkid"))
async def check_id_command(message: Message):
    """Показать текущие ID"""
    info = f"📊 Текущие настройки:\n\n• Канал: {PUBLIC_CHANNEL_ID}\n• Группа админов: {ADMIN_GROUP_ID}\n• Ваш ID: {message.from_user.id}"
    await message.answer(info)

# ========== АДМИН КОМАНДЫ ==========
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
                try:
                    await bot.send_message(
                        chat_id=PUBLIC_CHANNEL_ID,
                        text=f"🎮 Регистрация команд открыта!\nМаксимум: {MAX_TEAMS} команд\nИспользуйте /register. Создатель @cosinxx"
                    )
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
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
        f"📊 Статус:\n• Лимит: {MAX_TEAMS}\n• Зарегистрировано: {team_counter}\n"
        f"• Свободно: {MAX_TEAMS - team_counter}\n• Статус: {'✅ Открыта' if registration_active else '❌ Закрыта'}\n"
    )
    
    if teams_data:
        status_text += "\nКоманды:\n"
        for num, team in teams_data.items():
            status_text += f"#{num}: {team['name']} ({len(team['players'])} игроков)\n"
    
    await message.answer(status_text)

# ========== КОМАНДЫ ДЛЯ ВСЕХ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Бот регистрации команд\n"
        "Используйте /register для регистрации\n"
        "/help для списка команд"
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
    
    # ОБНОВЛЕННОЕ СООБЩЕНИЕ С НОВЫМ ФОРМАТОМ
    await message.answer(
        "✅ Аватарка принята!\n\n"
        "👥 Теперь введите данные игроков в формате:\n\n"
        "<code>ID ЮЗЕРНЕЙМ НИК</code>\n\n"
        "Пример для 3 игроков:\n"
        "<code>123456789 @username1 PlayerOne\n"
        "987654321 @username2 PlayerTwo\n"
        "555555555 @username3 PlayerThree</code>\n\n"
        "📌 Важные моменты:\n"
        "• ID - только цифры\n"
        "• Юзернейм - начинается с @\n"
        "• Ник - любое имя\n"
        "• Каждый игрок с новой строки"
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
    errors = []
    
    # Парсим данные игроков
    for i, line in enumerate(message.text.strip().split('\n')[:10]):
        parts = line.strip().split()
        
        if len(parts) >= 3:
            player_id = parts[0]
            username = parts[1]
            nickname = ' '.join(parts[2:])[:50]
            
            # Проверяем ID (только цифры)
            if not player_id.isdigit():
                errors.append(f"Строка {i+1}: ID '{player_id}' должен содержать только цифры")
                continue
            
            # Проверяем юзернейм (должен начинаться с @)
            if not username.startswith('@'):
                errors.append(f"Строка {i+1}: Юзернейм '{username}' должен начинаться с @")
                continue
            
            players.append({
                'id': player_id,
                'username': username,
                'nickname': nickname
            })
        else:
            errors.append(f"Строка {i+1}: Неверный формат. Нужно: ID @username Ник")
    
    # Если есть ошибки, показываем их
    if errors:
        error_text = "❌ Обнаружены ошибки:\n\n" + "\n".join(errors[:5])  # Показываем первые 5 ошибок
        if len(errors) > 5:
            error_text += f"\n\n... и еще {len(errors) - 5} ошибок"
        error_text += "\n\nИсправьте ошибки и отправьте данные снова:"
        await message.answer(error_text)
        return
    
    if not players:
        await message.answer("❌ Не удалось распознать данные игроков. Введите снова в правильном формате.")
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
        'captain': f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    }
    
    # Отправляем в канал (публичная информация)
    channel_success = False
    if PUBLIC_CHANNEL_ID:
        try:
            await bot.send_photo(
                chat_id=PUBLIC_CHANNEL_ID,
                photo=avatar_file_id,
                caption=f"🏆 Команда #{team_number}: {team_name}"
            )
            channel_success = True
        except Exception as e:
            error_msg = str(e)
            if "Chat not found" in error_msg:
                await message.answer("❌ Канал не найден. Проверьте ID канала.")
            elif "Forbidden" in error_msg:
                await message.answer("❌ Бот заблокирован в канале или не имеет прав.")
            else:
                await message.answer(f"❌ Ошибка отправки в канал: {error_msg}")
    
    # Отправляем админам (приватная информация с юзернеймами)
    admin_success = False
    if ADMIN_GROUP_ID:
        try:
            # Формируем детальную информацию об игроках
            players_info = []
            for p in players:
                players_info.append(f"👤 ID: {p['id']} | Юзернейм: {p['username']} | Ник: {p['nickname']}")
            
            players_text = "\n".join(players_info)
            
            admin_msg = (
                f"🔒 ПРИВАТНЫЕ ДАННЫЕ КОМАНДЫ\n\n"
                f"Команда #{team_number}: <b>{team_name}</b>\n"
                f"Капитан: {teams_data[team_number]['captain']}\n\n"
                f"📋 Полный состав:\n{players_text}\n\n"
                f"Всего игроков: {len(players)}"
            )
            
            await bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=admin_msg
            )
            admin_success = True
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить данные админам: {e}")
    
    # Увеличиваем счетчик команд
    team_counter += 1
    remaining = MAX_TEAMS - team_counter
    
    # Формируем отчет для капитана команды
    report = (
        f"✅ Команда <b>{team_name}</b> успешно зарегистрирована!\n\n"
        f"Номер команды: <b>#{team_number}</b>\n"
        f"Количество игроков: <b>{len(players)}</b>\n"
        f"Осталось мест: <b>{remaining}</b>\n\n"
    )
    
    # Добавляем информацию о том, куда отправлены данные
    if channel_success:
        report += "📢 Информация в канал: ✅ Отправлена\n"
    else:
        report += "📢 Информация в канал: ❌ Не отправлена\n"
    
    if admin_success:
        report += "🔒 Данные игроков админам: ✅ Отправлены"
    else:
        report += "🔒 Данные игроков админам: ❌ Не отправлены"
    
    # Показываем краткую информацию об игроках для подтверждения
    player_list = "\n".join([f"• {p['username']} ({p['nickname']})" for p in players])
    report += f"\n\n📋 Ваши игроки:\n{player_list}"
    
    await message.answer(report)
    
    # Проверяем, не заполнены ли все места
    if team_counter >= MAX_TEAMS:
        global registration_active
        registration_active = False
        
        # Уведомляем в канал о завершении регистрации
        if PUBLIC_CHANNEL_ID and channel_success:
            await bot.send_message(
                chat_id=PUBLIC_CHANNEL_ID,
                text="🎯 Регистрация завершена! Все места заняты."
            )
    
    await state.clear()

@dp.message(Command("teams"))
async def cmd_teams(message: Message):
    if not teams_data:
        await message.answer("📭 Нет зарегистрированных команд.")
        return
    
    text = f"📋 Зарегистрированные команды ({team_counter}/{MAX_TEAMS}):\n\n"
    for num, team in teams_data.items():
        player_count = len(team['players'])
        text += f"#{num}: <b>{team['name']}</b> ({player_count} игроков)\n"
    
    await message.answer(text)

@dp.message(Command("teamdetails"))
async def cmd_teamdetails(message: Message):
    """Показать детальную информацию о командах (только админ)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может просматривать детали.")
        return
    
    if not teams_data:
        await message.answer("📭 Нет зарегистрированных команд.")
        return
    
    for num, team in teams_data.items():
        players_info = []
        for i, player in enumerate(team['players'], 1):
            players_info.append(f"{i}. ID: {player['id']} | @{player['username']} | Ник: {player['nickname']}")
        
        players_text = "\n".join(players_info)
        
        team_info = (
            f"🔍 Команда #{num}: <b>{team['name']}</b>\n"
            f"Капитан: {team['captain']}\n"
            f"Игроков: {len(team['players'])}\n\n"
            f"Состав:\n{players_text}"
        )
        
        await message.answer(team_info)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Бот регистрации команд</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начало работы\n"
        "/register - Регистрация новой команды\n"
        "/teams - Просмотр зарегистрированных команд\n"
        "/help - Справка\n\n"
        
        "<b>Процесс регистрации команды:</b>\n"
        "1. Название команды\n"
        "2. Аватарка (логотип)\n"
        "3. Данные игроков в формате:\n"
        "   <code>ID @username Ник</code>\n\n"
        "Пример:\n"
        "<code>123456789 @player_one РусскийВоин\n"
        "987654321 @player_two Снайпер\n"
        "555555555 @player_tre Танк</code>\n\n"
        
        "<b>Команды проверки:</b>\n"
        "/testchannel - Проверить канал\n"
        "/checkid - Показать текущие настройки\n"
        "/getid - Получить ID чата"
    )
    
    # Добавляем команды админа
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "\n\n<b>👑 Команды администратора:</b>\n"
            "/setlimit - Установить лимит команд\n"
            "/closereg - Закрыть регистрацию\n"
            "/status - Показать статус регистрации\n"
            "/teamdetails - Детали всех команд"
        )
    
    await message.answer(help_text)

@dp.message(Command("getid"))
async def get_id_command(message: Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

@dp.message()
async def handle_other(message: Message):
    await message.answer("Неизвестная команда. Используйте /help для просмотра доступных команд.")

async def main():
    logger.info("Бот регистрации команд запущен!")
    logger.info(f"Канал для публикации: {PUBLIC_CHANNEL_ID}")
    logger.info(f"Группа для админов: {ADMIN_GROUP_ID}")
    
    # Проверяем подключение при запуске
    try:
        me = await bot.get_me()
        logger.info(f"Бот: @{me.username} ({me.id})")
        
        # Отправляем админу сообщение о запуске
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🤖 Бот @{me.username} запущен!\n"
                 f"Используйте /setlimit для начала регистрации.\n"
                 f"Новый формат данных игроков: ID @username Ник"
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
