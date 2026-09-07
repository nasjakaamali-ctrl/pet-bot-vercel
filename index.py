import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes

app = FastAPI()
TOKEN = os.environ.get("import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes

app = FastAPI()
TOKEN = os.environ.get("TELEGRAM_TOKEN", "8870623888:AAETQiAOvRCev75LDP1hADXwQB0uG0bs-mU") 

# Простая память для теста (в реальном проекте подключим базу позже)
user_states = {}

async def handle_step(user_id, chat_id, callback_data=None):
    state = user_states.get(user_id, "start")
    
    if state == "start":
        if callback_data == "action_start":
            user_states[user_id] = "pet_type"
            return "Кто у вас живёт?", InlineKeyboardMarkup([
                [InlineKeyboardButton(" Кошка", callback_data="type_cat")],
                [InlineKeyboardButton("🐶 Собака", callback_data="type_dog")]
            ])
        return "Привет! 👋 Соберём календарь ухода.", InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать", callback_data="action_start")]
        ])
        
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            user_states[user_id] = "completed"
            pet_name = "Кошка" if "cat" in callback_data else "Собака"
            return f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен.", None
            
    return "Что-то пошло не так. Напиши /start", None

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ApplicationBuilder().token(TOKEN).build())
    
    if update.callback_query:
        text, kb = await handle_step(update.effective_user.id, update.effective_chat.id, update.callback_query.data)
        if kb:
            await update.callback_query.edit_message_text(text, reply_markup=kb)
        else:
            await update.callback_query.message.reply_text(text)
            
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}", "8870623888:AAETQiAOvRCev75LDP1hADXwQB0uG0bs-mU") 

# Простая память для теста (в реальном проекте подключим базу позже)
user_states = {}

async def handle_step(user_id, chat_id, callback_data=None):
    state = user_states.get(user_id, "start")
    
    if state == "start":
        if callback_data == "action_start":
            user_states[user_id] = "pet_type"
            return "Кто у вас живёт?", InlineKeyboardMarkup([
                [InlineKeyboardButton(" Кошка", callback_data="type_cat")],
                [InlineKeyboardButton("🐶 Собака", callback_data="type_dog")]
            ])
        return "Привет! 👋 Соберём календарь ухода.", InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать", callback_data="action_start")]
        ])
        
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            user_states[user_id] = "completed"
            pet_name = "Кошка" if "cat" in callback_data else "Собака"
            return f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен.", None
            
    return "Что-то пошло не так. Напиши /start", None

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ApplicationBuilder().token(TOKEN).build())
    
    if update.callback_query:
        text, kb = await handle_step(update.effective_user.id, update.effective_chat.id, update.callback_query.data)
        if kb:
            await update.callback_query.edit_message_text(text, reply_markup=kb)
        else:
            await update.callback_query.message.reply_text(text)
            
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
