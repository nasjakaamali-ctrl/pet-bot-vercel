from fastapi import FastAPI, Request
import httpx
import json

app = FastAPI()
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Временная память вместо базы
user_states = {}

async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/sendMessage", json=payload)

def get_kb(buttons):
    return {"inline_keyboard": buttons}

async def handle_step(user_id, chat_id, message_id, callback_data=None, text=None):
    state = user_states.get(user_id, "new_user")
    response_text = ""
    keyboard = None
    next_state = state

    # --- ЛОГИКА СОСТОЯНИЙ ---
    if state == "new_user":
        if callback_data == "action_start" or (text and "/start" in text):
            next_state = "pet_type"
            response_text = "Кто у вас живёт?"
            keyboard = get_kb([[
                {"text": "🐱 Кошка", "callback_data": "type_cat"},
                {"text": " Собака", "callback_data": "type_dog"}
            ]])
            
    elif state == "pet_type":
        if callback_data and callback_data.startswith("type_"):
            next_state = "pets_count" 
            response_text = "Сколько питомцев?"
            keyboard = get_kb([
                [{"text": "1", "callback_data": "count_1"}],
                [{"text": "2", "callback_data": "count_2"}],
                [{"text": "3+", "callback_data": "count_3plus"}]
            ])

    elif state == "pets_count":
        if callback_data and callback_data.startswith("count_"):
            next_state = "common_schedule"
            response_text = "У них примерно одинаковый режим ухода?"
            keyboard = get_kb([
                [{"text": "Да, один режим", "callback_data": "mode_same"}],
                [{"text": "Нет, отдельно", "callback_data": "mode_diff"}]
            ])

    elif state == "common_schedule":
        if callback_data and callback_data.startswith("mode_"):
            next_state = "basic_schedule"
            response_text = "Добавить базовый уход (вода, корм, лоток)?"
            keyboard = get_kb([
                [{"text": "✅ Да, добавить всё", "callback_data": "base_yes"}],
                [{"text": "⚙️ Выбрать самому", "callback_data": "base_custom"}]
            ])

    elif state == "basic_schedule":
        if callback_data == "base_yes":
            next_state = "time_setup"
            response_text = "Когда удобнее получать напоминания?"
            keyboard = get_kb([
                [{"text": "19:00", "callback_data": "time_19"}],
                [{"text": "20:00", "callback_data": "time_20"}]
            ])
        else:
            next_state = "completed"
            response_text = "Календарь готов ✅"

    elif state == "time_setup":
        if callback_data and callback_data.startswith("time_"):
            next_state = "completed"
            response_text = "Готово ✅ Основной календарь настроен."
            keyboard = None

    elif state == "completed":
        response_text = "Календарь активен! 🐾"
        keyboard = None

    user_states[user_id] = next_state
    return response_text, keyboard

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
            
            text, kb = await handle_step(user_id, chat_id, message_id, callback_data=callback_data)
            
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
            
            text, kb = await handle_step(user_id, chat_id, None, text=text_msg)
            
            if kb:
                await send_message(chat_id, text, kb)
            else:
                await send_message(chat_id, text)
                
        return {"status": "ok"}
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
