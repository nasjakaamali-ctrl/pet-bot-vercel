import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder
from supabase import create_client, Client

# --- НАСТРОЙКИ ---
# Твой токен уже встроен
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw" 
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") 

app = FastAPI()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- СТРОГИЙ КОНЕЧНЫЙ АВТОМАТ (STATE MACHINE) ---
async def handle_step(user_id, chat_id, callback_data=None):
    # 1. Получаем или создаем пользователя
    res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        supabase.table("users").insert({
            "telegram_id": user_id, 
            "chat_id": chat_id, 
            "dialog_state": "new_user"
        }).execute()
        state = "new_user"
    else:
        state = user["dialog_state"]

    response_text = ""
    keyboard = None
    next_state = state

    # ШАГ 1: НОВЫЙ ПОЛЬЗОВАТЕЛЬ / СТАРТ (Промт п.6)
    if state == "new_user":
        response_text = "Привет! 👋\nСоберём календарь ухода. Без длинных анкет — просто несколько кнопок."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Настроить календарь", callback_data="action_start")]])
        
        if callback_data == "action_start":
            next_state = "pet_type"
            response_text = "Кто у вас живёт?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(" Кошка", callback_data="type_cat")],
                [InlineKeyboardButton("🐶 Собака", callback_data="type_dog")],
                [InlineKeyboardButton("🐾 Другой питомец", callback_data="type_other")]
            ])

    # ШАГ 2: ВИД ПИТОМЦА (Промт п.6)
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            pet_type = callback_data.split("_")[1]
            # Сохраняем тип питомца в БД
            supabase.table("pets").insert({"user_id": user['id'], "type": pet_type}).execute()
            
            next_state = "pets_count"
            response_text = "Сколько питомцев?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data="count_1")],
                [InlineKeyboardButton("2", callback_data="count_2")],
                [InlineKeyboardButton("3", callback_data="count_3")],
                [InlineKeyboardButton("4", callback_data="count_4")],
                [InlineKeyboardButton("5", callback_data="count_5")],
                [InlineKeyboardButton("6+", callback_data="count_6plus")]
            ])

    # ШАГ 3: КОЛИЧЕСТВО И РЕЖИМ (Промт п.6, п.27)
    elif state == "pets_count":
        if callback_data and callback_data.startswith("count_"):
            count_val = callback_data.split("_")[1]
            
            if count_val == "6plus":
                # Подшаг для 6+ питомцев
                next_state = "pets_count_6plus"
                response_text = "Укажите точное количество:"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("6", callback_data="count_6")],
                    [InlineKeyboardButton("7", callback_data="count_7")],
                    [InlineKeyboardButton("8", callback_data="count_8")],
                    [InlineKeyboardButton("9", callback_data="count_9")],
                    [InlineKeyboardButton("10", callback_data="count_10")],
                    [InlineKeyboardButton("Больше", callback_data="count_more")]
                ])
            else:
                # Переход к вопросу про режим
                next_state = "common_schedule"
                response_text = "У них примерно одинаковый режим ухода?"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Да, один режим", callback_data="mode_same")],
                    [InlineKeyboardButton("Нет, отдельно", callback_data="mode_diff")],
                    [InlineKeyboardButton("Потом разберём", callback_data="mode_later")]
                ])

    # ШАГ 3.1: УТОЧНЕНИЕ ДЛЯ 6+ (Промт п.6)
    elif state == "pets_count_6plus":
        if callback_data and callback_data.startswith("count_"):
            next_state = "common_schedule"
            response_text = "У них примерно одинаковый режим ухода?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Да, один режим", callback_data="mode_same")],
                [InlineKeyboardButton("Нет, отдельно", callback_data="mode_diff")],
                [InlineKeyboardButton("Потом разберём", callback_data="mode_later")]
            ])

    # ШАГ 4: ОБЩИЙ РЕЖИМ (Промт п.27)
    elif state == "common_schedule":
        if callback_data and callback_data.startswith("mode_"):
            next_state = "basic_schedule"
            response_text = "Могу сразу добавить базовый уход:\n✓ свежая вода\n✓ кормление\n✓ лоток\n✓ миски\n✓ быстрый осмотр\n\nДобавить?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, добавить всё", callback_data="base_yes")],
                [InlineKeyboardButton("⚙️ Выбрать самому", callback_data="base_custom")],
                [InlineKeyboardButton("Потом", callback_data="base_later")]
            ])

    # ШАГ 5: БАЗОВЫЙ КАЛЕНДАРЬ (Промт п.6)
    elif state == "basic_schedule":
        if callback_data == "base_yes":
            # Здесь позже добавим массовое создание задач в БД
            next_state = "time_setup"
            response_text = "Когда удобнее получать основные вечерние напоминания?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("18:00", callback_data="time_18")],
                [InlineKeyboardButton("19:00", callback_data="time_19")],
                [InlineKeyboardButton("20:00", callback_data="time_20")],
                [InlineKeyboardButton("Другое время", callback_data="time_other")]
            ])
        elif callback_data in ["base_custom", "base_later"]:
            next_state = "completed"
            response_text = "Основной календарь уже работает ✅\nМожно добавить ещё что-нибудь."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Здоровье", callback_data="opt_health")],
                [InlineKeyboardButton("Уход", callback_data="opt_care")],
                [InlineKeyboardButton("Запасы", callback_data="opt_stock")],
                [InlineKeyboardButton("Имена питомцев", callback_data="opt_names")],
                [InlineKeyboardButton("Закончить", callback_data="finish")]
            ])

    # ШАГ 6: ЗАВЕРШЕНИЕ / ОПЦИОНАЛЬНО (Промт п.10, п.33)
    elif state == "time_setup":
        if callback_data and callback_data.startswith("time_"):
            next_state = "completed"
            response_text = "Готово ✅ Основной календарь настроен.\nИмена и остальные детали можно добавить потом."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Закончить", callback_data="finish")],
                [InlineKeyboardButton("Настроить ещё", callback_data="optional_setup")]
            ])

    elif state == "completed":
        if callback_data == "finish":
            response_text = "Отлично! Календарь активен. Я буду присылать напоминания вовремя. 🐾"
            keyboard = None
            next_state = "idle" # Состояние покоя
        elif callback_data == "optional_setup":
            next_state = "optional_setup"
            response_text = "Что хотите настроить сейчас?"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Здоровье", callback_data="opt_health")],
                [InlineKeyboardButton("Уход", callback_data="opt_care")],
                [InlineKeyboardButton("Запасы", callback_data="opt_stock")],
                [InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]
            ])

    # Обновляем состояние пользователя в базе ТОЛЬКО если оно изменилось
    if user and next_state != state:
        supabase.table("users").update({"dialog_state": next_state}).eq("telegram_id", user_id).execute()
    
    return response_text, keyboard

# --- ОБРАБОТЧИК WEBHOOK ---
@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, ApplicationBuilder().token(TOKEN).build())
        
        # Обработка нажатий на кнопки
        if update.callback_query:
            text, kb = await handle_step(
                update.effective_user.id, 
                update.effective_chat.id, 
                update.callback_query.data
            )
            if kb:
                await update.callback_query.edit_message_text(text, reply_markup=kb)
            else:
                await update.callback_query.message.reply_text(text)
                
        return {"status": "ok"}
    except Exception as e:
        print(f"Error in webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
