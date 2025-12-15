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
import random
from datetime import datetime

# ========== ВАШИ ДАННЫЕ ==========
BOT_TOKEN = "7996038616:AAFZeaNCCYzPnubzDd6zMOLmOP_VrWdGiJM"
ADMIN_GROUP_ID = -5037361883  # Группа для админов
PUBLIC_CHANNEL_ID = -1003408636061  # Канал для публикации
# ВАШ ЛИЧНЫЙ ID и ID ВТОРОГО АДМИНА
ADMIN_IDS = [8272509909, 6925772057]  # ⚠️ Замените 1234567890 на ID второго админа

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
tournament_pairs = []

# Состояния
class TeamRegistration(StatesGroup):
    waiting_for_team_name = State()
    waiting_for_team_avatar = State()
    waiting_for_players = State()

class AdminSetLimit(StatesGroup):
    waiting_for_limit = State()

# ========== ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ПАР ТУРНИРА ==========
def create_tournament_pairs():
    """Создать случайные пары для турнира"""
    global tournament_pairs
    tournament_pairs = []
    
    if len(teams_data) < 2:
        return []
    
    team_numbers = list(teams_data.keys())
    random.shuffle(team_numbers)
    
    pairs = []
    for i in range(0, len(team_numbers), 2):
        if i + 1 < len(team_numbers):
            pairs.append((team_numbers[i], team_numbers[i + 1]))
        else:
            pairs.append((team_numbers[i], None))
    
    tournament_pairs = pairs
    return pairs

# ========== ФУНКЦИЯ ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЙ ВСЕМ АДМИНАМ ==========
async def send_to_all_admins(text: str):
    """Отправить сообщение всем админам"""
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.error(f"Не удалось отправить админу {admin_id}: {e}")

# ========== ФУНКЦИЯ ДЛЯ ОТПРАВКИ РАСПРЕДЕЛЕНИЯ АДМИНАМ ==========
async def send_tournament_distribution_to_admins():
    """Отправить распределение турнира админам"""
    if not tournament_pairs:
        return False
    
    try:
        distribution_text = "🎮 РАСПРЕДЕЛЕНИЕ КОМАНД ДЛЯ ТУРНИРА\n\n"
        distribution_text += f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        distribution_text += f"Всего команд: {len(teams_data)}\n"
        distribution_text += f"Количество матчей: {len(tournament_pairs)}\n\n"
        
        for match_num, (team1_num, team2_num) in enumerate(tournament_pairs, 1):
            distribution_text += f"⚔️ МАТЧ #{match_num}:\n"
            
            team1 = teams_data[team1_num]
            distribution_text += f"• Команда #{team1_num}: {team1['name']}\n"
            distribution_text += f"  Капитан: {team1['captain']}\n"
            
            if team2_num:
                team2 = teams_data[team2_num]
                distribution_text += f"• Команда #{team2_num}: {team2['name']}\n"
                distribution_text += f"  Капитан: {team2['captain']}\n"
            else:
                distribution_text += f"• 🎉 Команда #{team1_num} проходит автоматически\n"
            
            distribution_text += f"  📞 Контакты капитанов:\n"
            if team1['captain'].startswith('@'):
                distribution_text += f"  - {team1['captain']}\n"
            
            if team2_num and team2['captain'].startswith('@'):
                distribution_text += f"  - {team2['captain']}\n"
            
            distribution_text += "\n"
        
        distribution_text += "📋 Правила:\n"
        distribution_text += "1. Капитаны связываются для согласования времени\n"
        distribution_text += "2. Результаты отправляются организаторам\n"
        distribution_text += "3. Следующий этап будет объявлен после всех матчей\n"
        
        # Отправляем в группу админов
        await bot.send_message(chat_id=ADMIN_GROUP_ID, text=distribution_text)
        
        # Также отправляем всем админам лично
        await send_to_all_admins(
            f"✅ Распределение турнира отправлено в группу админов!\n"
            f"Всего матчей: {len(tournament_pairs)}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки распределения: {e}")
        return False

# ========== ФУНКЦИЯ ДЛЯ ОТПРАВКИ ПОЛНОГО СПИСКА В КАНАЛ ==========
async def send_all_teams_to_channel():
    """Отправить полный список всех команд в канал"""
    if not teams_data:
        return False
    
    try:
        summary = "📊 ПОЛНЫЙ СПИСОК ВСЕХ КОМАНД:\n\n"
        
        for team_num, team in teams_data.items():
            summary += f"🏆 КОМАНДА #{team_num}: {team['name']}\n"
            
            summary += "📋 Игроки:\n"
            for i, player in enumerate(team['players'], 1):
                summary += f"{i}. ID: {player['id']} | Юзернейм: {player['username']} | Ник: {player['nickname']}\n"
            
            summary += f"👥 Всего игроков: {len(team['players'])}\n"
            summary += "─" * 40 + "\n\n"
        
        summary += f"📈 ИТОГО: {len(teams_data)} команд, {sum(len(t['players']) for t in teams_data.values())} игроков"
        
        await bot.send_message(chat_id=PUBLIC_CHANNEL_ID, text=summary)
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки полного списка: {e}")
        return False

# ========== КОМАНДЫ ==========
@dp.message(Command("testchannel"))
async def test_channel_command(message: Message):
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
    info = f"📊 Текущие настройки:\n\n• Канал: {PUBLIC_CHANNEL_ID}\n• Группа админов: {ADMIN_GROUP_ID}\n• Ваш ID: {message.from_user.id}\n• Админы: {len(ADMIN_IDS)} пользователей\n• Зарегистрировано команд: {len(teams_data)}/{MAX_TEAMS}"
    await message.answer(info)

@dp.message(Command("getfull"))
async def cmd_getfull(message: Message):
    """Отправить полный список команд"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not teams_data:
        await message.answer("📭 Нет зарегистрированных команд.")
        return
    
    await send_all_teams_to_channel()
    await message.answer("✅ Полный список команд отправлен в канал!")

@dp.message(Command("makepairs"))
async def cmd_makepairs(message: Message):
    """Создать пары для турнира"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if len(teams_data) < 2:
        await message.answer("❌ Нужно минимум 2 команды.")
        return
    
    pairs = create_tournament_pairs()
    
    if not pairs:
        await message.answer("❌ Не удалось создать пары.")
        return
    
    result_text = "🎲 Созданы пары для турнира:\n\n"
    for match_num, (team1_num, team2_num) in enumerate(pairs, 1):
        team1 = teams_data[team1_num]
        if team2_num:
            team2 = teams_data[team2_num]
            result_text += f"Матч #{match_num}: {team1['name']} 🆚 {team2['name']}\n"
        else:
            result_text += f"Матч #{match_num}: {team1['name']} 🎉 (автоматический проход)\n"
    
    await message.answer(result_text)
    await send_tournament_distribution_to_admins()
    await message.answer("✅ Распределение отправлено админам!")

# ========== АДМИН КОМАНДЫ ==========
@dp.message(Command("setlimit"))
async def cmd_setlimit(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Только администратор.")
        return
    
    await state.set_state(AdminSetLimit.waiting_for_limit)
    await message.answer("Введите количество команд (1-20):")

@dp.message(AdminSetLimit.waiting_for_limit)
async def process_limit(message: Message, state: FSMContext):
    global MAX_TEAMS, registration_active, team_counter, teams_data, tournament_pairs
    
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 20:
            MAX_TEAMS = limit
            registration_active = True
            team_counter = 0
            teams_data = {}
            tournament_pairs = []
            
            await message.answer(f"✅ Лимит: {MAX_TEAMS} команд\nРегистрация открыта!")
            
            if PUBLIC_CHANNEL_ID:
                try:
                    await bot.send_message(
                        chat_id=PUBLIC_CHANNEL_ID,
                        text=f"🎮 Регистрация команд открыта!\nМаксимум: {MAX_TEAMS} команд\nИспользуйте /register"
                    )
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
            
            # Уведомляем всех админов
            admin_name = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            await send_to_all_admins(
                f"📢 Админ {admin_name} открыл регистрацию!\n"
                f"Лимит: {MAX_TEAMS} команд\n"
                f"Время: {datetime.now().strftime('%H:%M')}"
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
    if message.from_user.id not in ADMIN_IDS:
        return
    
    global registration_active
    registration_active = False
    
    await message.answer("✅ Регистрация закрыта.")
    
    if PUBLIC_CHANNEL_ID:
        await bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text="⛔ Регистрация команд закрыта."
        )
    
    # Уведомляем всех админов
    admin_name = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    await send_to_all_admins(
        f"📢 Админ {admin_name} закрыл регистрацию!\n"
        f"Время: {datetime.now().strftime('%H:%M')}"
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    status_text = f"📊 Статус:\n• Лимит: {MAX_TEAMS}\n• Зарегистрировано: {team_counter}\n• Свободно: {MAX_TEAMS - team_counter}\n• Статус: {'✅ Открыта' if registration_active else '❌ Закрыта'}\n• Пар создано: {len(tournament_pairs)}\n• Админов: {len(ADMIN_IDS)}\n"
    
    if teams_data:
        status_text += "\nКоманды:\n"
        for num, team in teams_data.items():
            status_text += f"#{num}: {team['name']} ({len(team['players'])} игроков)\n"
    
    await message.answer(status_text)

@dp.message(Command("whoami"))
async def cmd_whoami(message: Message):
    """Показать права пользователя"""
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Без username"
    
    if user_id in ADMIN_IDS:
        role = "👑 АДМИНИСТРАТОР"
        commands = "Доступны все админ-команды"
    else:
        role = "👤 ПОЛЬЗОВАТЕЛЬ"
        commands = "Доступны только обычные команды"
    
    info = (
        f"👤 Информация о вас:\n\n"
        f"• ID: {user_id}\n"
        f"• Username: {username}\n"
        f"• Роль: {role}\n"
        f"• Команды: {commands}\n\n"
        f"Админы бота: {len(ADMIN_IDS)} пользователей"
    )
    
    await message.answer(info)

# ========== КОМАНДЫ ДЛЯ ВСЕХ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("👋 Бот регистрации команд\nИспользуйте /register для регистрации\n/help для списка команд")

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
        "👥 Теперь введите данные игроков:\n\n"
        "<code>ID @username Ник</code>\n\n"
        "Пример:\n"
        "<code>123456789 @username1 PlayerOne\n"
        "987654321 @username2 PlayerTwo</code>"
    )

@dp.message(TeamRegistration.waiting_for_team_avatar)
async def wrong_avatar(message: Message):
    await message.answer("❌ Отправьте фото.")

@dp.message(TeamRegistration.waiting_for_players)
async def process_players(message: Message, state: FSMContext):
    global team_counter, registration_active, tournament_pairs
    
    if team_counter >= MAX_TEAMS:
        await message.answer("❌ Все места уже заняты!")
        await state.clear()
        return
    
    players = []
    errors = []
    
    for i, line in enumerate(message.text.strip().split('\n')[:10]):
        parts = line.strip().split()
        
        if len(parts) >= 3:
            player_id = parts[0]
            username = parts[1]
            nickname = ' '.join(parts[2:])[:50]
            
            if not player_id.isdigit():
                errors.append(f"Строка {i+1}: ID '{player_id}' должен содержать только цифры")
                continue
            
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
    
    if errors:
        error_text = "❌ Обнаружены ошибки:\n\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            error_text += f"\n\n... и еще {len(errors) - 5} ошибок"
        error_text += "\n\nИсправьте ошибки и отправьте данные снова:"
        await message.answer(error_text)
        return
    
    if not players:
        await message.answer("❌ Не удалось распознать данные игроков.")
        return
    
    data = await state.get_data()
    team_name = data.get('team_name')
    avatar_file_id = data.get('avatar_file_id')
    
    team_number = team_counter + 1
    teams_data[team_number] = {
        'name': team_name,
        'avatar': avatar_file_id,
        'players': players,
        'captain': f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    }
    
    # Отправляем в канал
    if PUBLIC_CHANNEL_ID:
        try:
            player_nicks = []
            for i, player in enumerate(players, 1):
                player_nicks.append(f"{i}. {player['nickname']}")
            
            players_text = "\n".join(player_nicks)
            
            channel_caption = (
                f"🏆 Команда #{team_number}: <b>{team_name}</b>\n\n"
                f"📋 Состав команды (ники):\n"
                f"{players_text}\n\n"
                f"👥 Всего игроков: {len(players)}"
            )
            
            await bot.send_photo(
                chat_id=PUBLIC_CHANNEL_ID,
                photo=avatar_file_id,
                caption=channel_caption
            )
        except Exception as e:
            error_msg = str(e)
            if "Chat not found" in error_msg:
                await message.answer("❌ Канал не найден.")
            elif "Forbidden" in error_msg:
                await message.answer("❌ Бот заблокирован в канале.")
            else:
                await message.answer(f"❌ Ошибка отправки в канал: {error_msg}")
    
    # Отправляем админам
    if ADMIN_GROUP_ID:
        try:
            players_info = []
            for i, player in enumerate(players, 1):
                players_info.append(f"{i}. ID: {player['id']} | Юзернейм: {player['username']} | Ник: {player['nickname']}")
            
            players_text = "\n".join(players_info)
            
            admin_msg = (
                f"🔒 ПРИВАТНЫЕ ДАННЫЕ КОМАНДЫ\n\n"
                f"Команда #{team_number}: <b>{team_name}</b>\n"
                f"Капитан: {teams_data[team_number]['captain']}\n\n"
                f"📋 Полный состав:\n"
                f"{players_text}\n\n"
                f"👥 Всего игроков: {len(players)}"
            )
            
            await bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_msg)
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить данные админам: {e}")
    
    team_counter += 1
    remaining = MAX_TEAMS - team_counter
    
    report = (
        f"✅ Команда <b>{team_name}</b> успешно зарегистрирована!\n\n"
        f"Номер команды: <b>#{team_number}</b>\n"
        f"Количество игроков: <b>{len(players)}</b>\n"
        f"Осталось мест: <b>{remaining}</b>"
    )
    
    await message.answer(report)
    
    # Проверяем, все ли команды собраны
    if team_counter >= MAX_TEAMS:
        registration_active = False
        
        if PUBLIC_CHANNEL_ID:
            try:
                await bot.send_message(
                    chat_id=PUBLIC_CHANNEL_ID,
                    text="🎯 Регистрация завершена! Все места заняты.\n\n📊 Полный список всех команд будет отправлен через 5 секунд..."
                )
                
                await asyncio.sleep(5)
                await send_all_teams_to_channel()
                
                await asyncio.sleep(3)
                pairs = create_tournament_pairs()
                
                if pairs:
                    await send_tournament_distribution_to_admins()
                    
                    await bot.send_message(
                        chat_id=PUBLIC_CHANNEL_ID,
                        text="🎲 Пары для турнира созданы и отправлены организаторам!"
                    )
                
                # Уведомляем всех админов
                await send_to_all_admins(
                    f"🎉 Регистрация полностью завершена!\n"
                    f"Всего команд: {len(teams_data)}\n"
                    f"Всего игроков: {sum(len(t['players']) for t in teams_data.values())}\n"
                    f"Пар создано: {len(pairs) if pairs else 0}"
                )
                
            except Exception as e:
                logger.error(f"Ошибка при завершении: {e}")
    
    await state.clear()

@dp.message(Command("showpairs"))
async def cmd_showpairs(message: Message):
    """Показать созданные пары"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not tournament_pairs:
        await message.answer("📭 Пары еще не созданы.")
        return
    
    pairs_text = "🎮 СОЗДАННЫЕ ПАРЫ ДЛЯ ТУРНИРА:\n\n"
    
    for match_num, (team1_num, team2_num) in enumerate(tournament_pairs, 1):
        team1 = teams_data[team1_num]
        pairs_text += f"⚔️ МАТЧ #{match_num}:\n"
        pairs_text += f"• Команда #{team1_num}: {team1['name']}\n"
        
        if team2_num:
            team2 = teams_data[team2_num]
            pairs_text += f"• Команда #{team2_num}: {team2['name']}\n"
            pairs_text += f"  🆚 {team1['name']} vs {team2['name']}\n"
        else:
            pairs_text += f"• 🎉 Команда #{team1_num} проходит автоматически\n"
        
        pairs_text += "\n"
    
    await message.answer(pairs_text)

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

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Бот регистрации команд</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начало работы\n"
        "/register - Регистрация команды\n"
        "/teams - Просмотр команд\n"
        "/help - Справка\n"
        "/whoami - Мои права\n\n"
        
        "<b>Формат данных игроков:</b>\n"
        "<code>ID @username Ник</code>\n\n"
        "Пример:\n"
        "<code>123456789 @ivanov Иван\n"
        "987654321 @petrov Петр</code>"
    )
    
    if message.from_user.id in ADMIN_IDS:
        help_text += (
            "\n\n<b>👑 Команды администратора:</b>\n"
            "/setlimit - Установить лимит команд\n"
            "/closereg - Закрыть регистрацию\n"
            "/status - Показать статус\n"
            "/getfull - Отправить полный список в канал\n"
            "/makepairs - Создать пары для турнира\n"
            "/showpairs - Показать созданные пары\n"
            "/testchannel - Проверить канал\n"
            "/checkid - Показать настройки"
        )
    
    await message.answer(help_text)

@dp.message(Command("getid"))
async def get_id_command(message: Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

@dp.message()
async def handle_other(message: Message):
    await message.answer("Неизвестная команда. Используйте /help")

async def main():
    logger.info("=" * 50)
    logger.info("Бот с двумя админами запущен!")
    logger.info(f"Админы: {ADMIN_IDS}")
    logger.info(f"Канал: {PUBLIC_CHANNEL_ID}")
    logger.info("=" * 50)
    
    try:
        me = await bot.get_me()
        logger.info(f"Бот: @{me.username} ({me.id})")
        
        # Отправляем всем админам сообщение о запуске
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"🤖 Бот @{me.username} запущен!\n\n"
                         f"Вы являетесь администратором.\n"
                         f"Всего админов: {len(ADMIN_IDS)}\n\n"
                         f"Используйте /setlimit для начала регистрации."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить админу {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
