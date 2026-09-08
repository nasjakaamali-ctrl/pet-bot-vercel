from fastapi import FastAPI, Request
import httpx
import json

app = FastAPI()
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Простая память
user_states = {}

async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/sendMessage", json=payload)

async def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
        
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE_URL}/editMessageText", json=payload)

def get_keyboard(buttons_data):
    """Превращает список кнопок в формат Telegram"""
    keyboard = []
    for row in buttons_data:
        keyboard_row = []
        for label, callback in row:
            keyboard_row.append({"text": label, "callback_data": callback})
        keyboard.append(keyboard_row)
    return {"inline_keyboard": keyboard}

@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        
        # Ручной парсинг update (самый надежный для Vercel)
        if "callback_query" in data:
            cq = data["callback_query"]
            user_id = cq["from"]["id"]
            chat_id = cq["message"]["chat"]["id"]
            message_id = cq["message"]["message_id"]
            callback_data = cq.get("data")
            
            state = user_states.get(user_id, "new_user")
            text = ""
            kb = None
            
            # ЛОГИКА СОСТОЯНИЙ
            if state == "new_user":
                if callback_data == "action_start":
                    user_states[user_id] = "pet_type"
                    text = "Кто у вас живёт?"
                    kb = get_keyboard([
                        [(" Кошка", "type_cat"), ("🐶 Собака", "type_dog")]
                    ])
                else:
                    text = "Привет! 👋 Соберём календарь ухода."
                    kb = get_keyboard([[("Настроить календарь", "action_start")]])
                    
            elif state == "pet_type":
                if callback_data and callback_data.startswith("type_"):
                    user_states[user_id] = "completed"
                    pet_name = "Кошка" if "cat" in callback_data else "Собака"
                    text = f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен."
                    # kb = None -> просто текст
                    
            # ОТПРАВКА ОТВЕТА
            if kb:
                await edit_message(chat_id, message_id, text, kb)
            else:
                await send_message(chat_id, text)
                
        return {"status": "ok"}
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error"}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
