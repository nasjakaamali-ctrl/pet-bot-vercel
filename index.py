from fastapi import FastAPI, Request
import httpx
import json
import re
from supabase import create_client, Client

app = FastAPI()

# --- НАСТРОЙКИ (ВСТАВЛЕНЫ ТВОИ ДАННЫЕ) ---
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw"
SUPABASE_URL = "https://plwizboccrdnpjxljoed.supabase.co"
SUPABASE_KEY = "sb_secret_b-yoFat4aqDr1v-oPNX1lg_gCQdproE"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/sendMessage", json=payload)

def get_kb(buttons):
    return {"inline_keyboard": buttons}

# --- РАСПОЗНАВАНИЕ ЕСТЕСТВЕННОГО ЯЗЫКА (п. 14, 15) ---
def parse_natural_language(text):
    text_lower = text.lower()
    result = {}
    
    if any(w in text_lower for w in ["кошк", "кот", "cat"]):
        result["pet_type"] = "cat"
    elif any(w in text_lower for w in ["собак", "dog", "пёс"]):
        result["pet_type"] = "dog"
        
    count_match = re.search(r'(\d+)\s*(?:кошек|собак|питомцев|животных)', text_lower)
    if count_match:
        result["count"] = int(count_match.group(1))
    elif "6+" in text or "шесть" in text_lower or "много" in text_lower:
        result["count"] = 6
        
    time_match = re.search(r'(\d{1,2})[:\.](\d{2})', text)
    if time_match:
        result["time"] = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
    elif "утром" in text_lower:
        result["time"] = "08:00"
    elif "вечером" in text_lower:
        result["time"] = "19:00"
        
    if "воду" in text_lower or "поить" in text_lower:
        result["task"] = "water"
    elif "корм" in text_lower or "еда" in text_lower:
        result["task"] = "food"
    elif "лоток" in text_lower or "туалет" in text_lower:
        result["task"] = "litter"
        
    return result

# --- ГЛАВНАЯ ЛОГИКА СОСТОЯНИЙ ---
async def handle_step(user_id, chat_id, message_id, callback_data=None, text=None):
    res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        supabase.table("users").insert({
            "telegram_id": user_id, 
            "chat_id": chat_id, 
            "dialog_state": "new_user",
            "tariff": "free"
        }).execute()
        state = "new_user"
        tariff = "free"
    else:
        state = user["dialog_state"]
        tariff = user.get("tariff", "free")

    response_text = ""
    keyboard = None
    next_state = state
    
    # ПРОВЕРКА ТАРИФА (п. 29)
    is_premium_action = callback_data in ["opt_health", "opt_stock", "base_custom"]
    if is_premium_action and tariff == "free":
        response_text = "️ Эта функция доступна на тарифе Premium.\n\nХотите обновить тариф?"
        keyboard = get_kb([[{"text": "💎 Обновить тариф", "callback_data": "upgrade_tariff"}]])
        return response_text, keyboard, next_state

    # --- ШАГ 1: СТАРТ / НОВЫЙ ПОЛЬЗОВАТЕЛЬ ---
    if state == "new_user":
        if callback_data == "action_start" or (text and "/start" in text):
            next_state = "pet_type"
            response_text = "Кто у вас живёт?"
            keyboard = get_kb([[
                {"text": " Кошка", "callback_data": "type_cat"},
                {"text": "🐶 Собака", "callback_data": "type_dog"},
                {"text": "🐾 Другой", "callback_data": "type_other"}
            ]])
            
        elif text:
            parsed = parse_natural_language(text)
            if "pet_type" in parsed:
                supabase.table("pets").insert({"user_id": user['id'], "type": parsed["pet_type"]}).execute()
                next_state = "pets_count"
                response_text = "Сколько питомцев?"
                keyboard = get_kb([
                    [{"text": "1", "callback_data": "count_1"}],
                    [{"text": "2", "callback_data": "count_2"}],
                    [{"text": "3+", "callback_data": "count_3plus"}]
                ])
            else:
                response_text = "Привет! 👋 Нажми кнопку ниже, чтобы начать."
                keyboard = get_kb([[{"text": "Настроить календарь", "callback_data": "action_start"}]])

    # --- ШАГ 2: ВИД ПИТОМЦА ---
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            pet_type = callback_data.split("_")[1]
            supabase.table("pets").insert({"user_id": user['id'], "type": pet_type}).execute()
            
            next_state = "pets_count"
            response_text = "Сколько питомцев?"
            keyboard = get_kb([
                [{"text": "1", "callback_data": "count_1"}],
                [{"text": "2", "callback_data": "count_2"}],
                [{"text": "3", "callback_data": "count_3"}],
                [{"text": "4", "callback_data": "count_4"}],
                [{"text": "5", "callback_data": "count_5"}],
                [{"text": "6+", "callback_data": "count_6plus"}]
            ])

    # --- ШАГ 3: КОЛИЧЕСТВО ---
    elif state == "pets_count":
        if callback_data and callback_data.startswith("count_"):
            count_val = callback_data.split("_")[1]
            
            if count_val == "6plus":
                next_state = "pets_count_6plus"
                response_text = "Укажите точное количество:"
                keyboard = get_kb([
                    [{"text": "6", "callback_data": "count_6"}],
                    [{"text": "7", "callback_data": "count_7"}],
                    [{"text": "8", "callback_data": "count_8"}],
                    [{"text": "9", "callback_data": "count_9"}],
                    [{"text": "10", "callback_data": "count_10"}],
                    [{"text": "Больше", "callback_data": "count_more"}]
                ])
            else:
                next_state = "common_schedule"
                response_text = "У них примерно одинаковый режим ухода? (п. 27)"
                keyboard = get_kb([
                    [{"text": "Да, один режим", "callback_data": "mode_same"}],
                    [{"text": "Нет, отдельно", "callback_data": "mode_diff"}],
                    [{"text": "Потом разберём", "callback_data": "mode_later"}]
                ])

    # --- ШАГ 3.1: УТОЧНЕНИЕ 6+ ---
    elif state == "pets_count_6plus":
        if callback_data and callback_data.startswith("count_"):
            next_state = "common_schedule"
            response_text = "У них примерно одинаковый режим ухода?"
            keyboard = get_kb([
                [{"text": "Да, один режим", "callback_data": "mode_same"}],
                [{"text": "Нет, отдельно", "callback_data": "mode_diff"}]
            ])

    # --- ШАГ 4: ОБЩИЙ РЕЖИМ ---
    elif state == "common_schedule":
        if callback_data and callback_data.startswith("mode_"):
            next_state = "basic_schedule"
            response_text = "Могу сразу добавить базовый уход (п. 6):\n✓ свежая вода\n✓ кормление\n✓ лоток\n✓ миски\n✓ быстрый осмотр\n\nДобавить?"
            keyboard = get_kb([
                [{"text": "✅ Да, добавить всё", "callback_data": "base_yes"}],
                [{"text": "⚙️ Выбрать самому", "callback_data": "base_custom"}],
                [{"text": "Потом", "callback_data": "base_later"}]
            ])

    # --- ШАГ 5: БАЗОВЫЙ КАЛЕНДАРЬ ---
    elif state == "basic_schedule":
        if callback_data == "base_yes":
            next_state = "time_setup"
            response_text = "Когда удобнее получать основные вечерние напоминания? (п. 8)"
            keyboard = get_kb([
                [{"text": "18:00", "callback_data": "time_18"}],
                [{"text": "19:00", "callback_data": "time_19"}],
                [{"text": "20:00", "callback_data": "time_20"}],
                [{"text": "Другое время", "callback_data": "time_other"}]
            ])
        elif callback_data in ["base_custom", "base_later"]:
            next_state = "completed"
            response_text = "Основной календарь уже работает ✅\nМожно добавить ещё что-нибудь (п. 10)."
            keyboard = get_kb([
                [{"text": "Здоровье", "callback_data": "opt_health"}],
                [{"text": "Уход", "callback_data": "opt_care"}],
                [{"text": "Запасы", "callback_data": "opt_stock"}],
                [{"text": "Имена питомцев", "callback_data": "opt_names"}],
                [{"text": "Закончить", "callback_data": "finish"}]
            ])

    # --- ШАГ 6: НАСТРОЙКА ВРЕМЕНИ ---
    elif state == "time_setup":
        if callback_data and callback_data.startswith("time_"):
            next_state = "completed"
            response_text = "Готово ✅ Основной календарь настроен.\nИмена и остальные детали можно добавить потом (п. 33)."
            keyboard = get_kb([
                [{"text": "Закончить", "callback_data": "finish"}],
                [{"text": "Настроить ещё", "callback_data": "optional_setup"}]
            ])

    # --- ШАГ 7: ЗАВЕРШЕНИЕ / ОПЦИОНАЛЬНО ---
    elif state == "completed":
        if callback_data == "finish":
            response_text = "Отлично! Календарь активен. Я буду присылать напоминания вовремя. 🐾 (п. 35)"
            keyboard = None
            next_state = "idle"
        elif callback_data == "optional_setup":
            next_state = "optional_setup"
            response_text = "Что хотите настроить сейчас?"
            keyboard = get_kb([
                [{"text": "Здоровье", "callback_data": "opt_health"}],
                [{"text": "Уход", "callback_data": "opt_care"}],
                [{"text": "Запасы", "callback_data": "opt_stock"}],
                [{"text": "Вернуться в меню", "callback_data": "back_to_menu"}]
            ])

    # --- ОБНОВЛЕНИЕ СОСТОЯНИЯ В БД ---
    if user and next_state != state:
        supabase.table("users").update({"dialog_state": next_state}).eq("telegram_id", user_id).execute()
    
    return response_text, keyboard, next_state

# --- WEBHOOK ---
@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        
        if "callback_query" in data:
            cq = data["callback_query"]
            user_id = cq["from"]["id"]
            chat_id = cq["message"]["chat"]["id"]
            message_id = cq["message"]["message_id"]
            callback_data = cq.get("data")
            
            text, kb, _ = await handle_step(user_id, chat_id, message_id, callback_data=callback_data)
            
            if kb:
                payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "reply_markup": json.dumps(kb)}
                async with httpx.AsyncClient() as client:
                    await client.post(f"{BASE_URL}/editMessageText", json=payload)
            else:
                await send_message(chat_id, text)
                
        elif "message" in data:
            msg = data["message"]
            user_id = msg["from"]["id"]
            chat_id = msg["chat"]["id"]
            text_msg = msg.get("text", "")
            
            text, kb, _ = await handle_step(user_id, chat_id, None, text=text_msg)
            
            if kb:
                await send_message(chat_id, text, kb)
            else:
                await send_message(chat_id, text)
                
        return {"status": "ok"}
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
