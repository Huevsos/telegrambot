import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

# Настройки бота
BOT_TOKEN = "8126450707:AAHQVuPw4cmJ9SppL6VOfcwd99UnuXNZvG4"  # Ваш токен
ADMIN_ID = 7433757951  # Замените на ваш ID в Telegram

# Хранилище данных (в реальном боте используйте БД)
referral_data = {}  # user_id: {"referrals": [], "referrer": None}

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли реферальная ссылка
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        try:
            referrer_id = int(referrer_id)
            # Сохраняем реферера
            if user_id not in referral_data:
                referral_data[user_id] = {"referrals": [], "referrer": referrer_id}
            
            # Добавляем реферала к рефереру
            if referrer_id in referral_data:
                if user_id not in referral_data[referrer_id]["referrals"]:
                    referral_data[referrer_id]["referrals"].append(user_id)
            else:
                referral_data[referrer_id] = {"referrals": [user_id], "referrer": None}
            
            await message.answer(
                f"🎉 Вы зарегистрировались по реферальной ссылке пользователя {referrer_id}!\n\n"
                "Используйте /help чтобы увидеть доступные команды"
            )
            
            # Уведомляем реферера
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎯 У вас новый реферал! Пользователь @{message.from_user.username or user_id} присоединился по вашей ссылке.\n"
                    f"Всего рефералов: {len(referral_data[referrer_id]['referrals'])}"
                )
            except:
                pass
                
        except ValueError:
            await message.answer("Добро пожаловать! Используйте /help")
    else:
        # Обычный старт без реферальной ссылки
        if user_id not in referral_data:
            referral_data[user_id] = {"referrals": [], "referrer": None}
        
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Это реферальный бот. Приглашайте друзей и получайте бонусы!\n\n"
            f"Ваша реферальная ссылка:\n"
            f"https://t.me/{(await bot.get_me()).username}?start={user_id}\n\n"
            "Используйте /ref чтобы увидеть статистику"
        )

# Команда /ref - статистика рефералов
@dp.message(Command("ref"))
async def cmd_ref(message: Message):
    user_id = message.from_user.id
    
    if user_id not in referral_data:
        referral_data[user_id] = {"referrals": [], "referrer": None}
    
    ref_count = len(referral_data[user_id]["referrals"])
    referrer = referral_data[user_id].get("referrer")
    
    text = (
        f"📊 Ваша реферальная статистика:\n\n"
        f"👥 Количество рефералов: {ref_count}\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"https://t.me/{(await bot.get_me()).username}?start={user_id}\n\n"
    )
    
    if referrer:
        text += f"🤝 Вас пригласил: пользователь {referrer}"
    else:
        text += "❌ Вас никто не пригласил"
    
    await message.answer(text)

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📚 Доступные команды:\n\n"
        "/start - Запустить бота\n"
        "/ref - Посмотреть реферальную статистику\n"
        "/help - Показать это сообщение\n\n"
        "🔗 Чтобы пригласить друга, просто отправьте ему вашу реферальную ссылку из команды /ref"
    )
    await message.answer(help_text)

# Команда /admin для администратора
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    global ADMIN_ID
    
    # Первый пользователь, написавший /admin становится администратором
    if ADMIN_ID is None:
        ADMIN_ID = message.from_user.id
        await message.answer("✅ Вы назначены администратором!")
    
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора")
        return
    
    # Статистика бота
    total_users = len(referral_data)
    total_refs = sum(len(data["referrals"]) for data in referral_data.values())
    
    admin_text = (
        f"👑 Админ-панель\n\n"
        f"👤 Всего пользователей: {total_users}\n"
        f"🔗 Всего рефералов: {total_refs}\n"
        f"📈 Среднее количество рефералов: {total_refs/total_users if total_users > 0 else 0:.2f}"
    )
    
    await message.answer(admin_text)

# Основная функция
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
