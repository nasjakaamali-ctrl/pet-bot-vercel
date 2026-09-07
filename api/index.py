import os
import json
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

app = FastAPI()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO)

# --- ЛОГИКА СОСТОЯНИЙ ---
async def handle_step(user_id, chat_id, text, callback_data=None):
    # Получаем текущее состояние
    res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        supabase.table("users").insert({"telegram_id": user_id, "chat_id": chat_id}).execute()
        state = "start"
    else:
        state = user["dialog_state"]

    response_text = ""
    keyboard = None
    next_state = state

    # ШАГ 1: СТАРТ
    if state == "start":
        response_text = "Привет! 👋 Соберём календарь ухода. Без длинных анкет — просто несколько кнопок."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Начать", callback_data="action_start")]
        ])
        if callback_data == "action_start":
            next_state = "pet_type"
            response_text = "Кто у вас живёт?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🐱 Кошка", callback_data="type_cat")],
                [InlineKeyboardButton("🐶 Собака", callback_data="type_dog")],
                [InlineKeyboardButton("🐾 Другой", callback_data="type_other")]
            ])

    # ШАГ 2: ВИД ПИТОМЦА
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            pet_type = callback_data.split("_")[1]
            # Сохраняем тип питомца
            supabase.table("pets").insert({"user_id": user['id'], "type": pet_type}).execute()
            
            next_state = "pets_count"
            response_text = "Сколько питомцев?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data="count_1")],
                [InlineKeyboardButton("2", callback_data="count_2")],
                [InlineKeyboardButton("3+", callback_data="count_3plus")]
            ])

    # ШАГ 3: КОЛИЧЕСТВО
    elif state == "pets_count":
        if callback_data and callback_data.startswith("count_"):
            next_state = "basic_schedule"
            response_text = "Добавить базовый уход (вода, корм, лоток)?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, добавить всё", callback_data="base_yes")],
                [InlineKeyboardButton("️ Выбрать самому", callback_data="base_custom")]
            ])

    # ШАГ 4: БАЗОВЫЙ КАЛЕНДАРЬ
    elif state == "basic_schedule":
        if callback_data == "base_yes":
            # Здесь позже добавим создание задач в БД
            next_state = "completed"
            response_text = "Готово ✅ Основной календарь настроен. Имена можно добавить потом."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Закончить", callback_data="finish")]
            ])

    # Обновляем состояние пользователя
    if user:
        supabase.table("users").update({"dialog_state": next_state}).eq("telegram_id", user_id).execute()
    
    return response_text, keyboard

async def handle_update(update: Update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Обработка кнопок
    if update.callback_query:
        query = update.callback_query
        text, kb = await handle_step(user_id, chat_id, None, query.data)
        if kb:
            await query.edit_message_text(text, reply_markup=kb)
        else:
            await query.message.reply_text(text)
            
    # Обработка текста
    elif update.message and update.message.text:
        text, kb = await handle_step(user_id, chat_id, update.message.text)
        if kb:
            await update.message.reply_text(text, reply_markup=kb)
        else:
            await update.message.reply_text(text)

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ApplicationBuilder().token(TELEGRAM_TOKEN).build())
    await handle_update(update, None)
    return {"status": "ok"}

@app.get("/")
async def set_webhook():
    bot_url = f"https://{os.environ.get('VERCEL_URL')}/"
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    await app_bot.bot.set_webhook(bot_url)
    return {"message": f"Webhook set to {bot_url}"}
