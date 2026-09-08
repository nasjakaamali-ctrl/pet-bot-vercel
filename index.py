from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
import asyncio

app = FastAPI()
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw" 

# Создаем объект бота напрямую (без ApplicationBuilder)
bot = Bot(token=TOKEN)

# Простая память для теста
user_states = {}

async def handle_step(user_id, callback_data=None):
    state = user_states.get(user_id, "new_user")
    
    if state == "new_user":
        if callback_data == "action_start":
            user_states[user_id] = "pet_type"
            return "Кто у вас живёт?", InlineKeyboardMarkup([
                [InlineKeyboardButton("🐱 Кошка", callback_data="type_cat")],
                [InlineKeyboardButton("🐶 Собака", callback_data="type_dog")]
            ])
        return "Привет! 👋 Соберём календарь ухода.", InlineKeyboardMarkup([
            [InlineKeyboardButton("Настроить календарь", callback_data="action_start")]
        ])
        
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            user_states[user_id] = "completed"
            pet_name = "Кошка" if "cat" in callback_data else "Собака"
            return f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен.", None
            
    return "Напиши /start", None

@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)
        
        if update.callback_query:
            text, kb = await handle_step(update.effective_user.id, update.callback_query.data)
            
            # Явная отправка сообщений через объект bot
            if kb:
                await bot.edit_message_text(
                    chat_id=update.callback_query.message.chat_id,
                    message_id=update.callback_query.message.message_id,
                    text=text,
                    reply_markup=kb
                )
            else:
                await bot.send_message(
                    chat_id=update.callback_query.message.chat_id,
                    text=text
                )
                
        return {"status": "ok"}
    except Exception as e:
        # Выводим ошибку в логи Vercel, чтобы видеть её
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
