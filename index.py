from fastapi import FastAPI, Request
import httpx
import json

app = FastAPI()
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}

async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/sendMessage", json=payload)
        return resp.status_code == 200

@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        
        # Обработка кнопок
        if "callback_query" in data:
            cq = data["callback_query"]
            user_id = cq["from"]["id"]
            chat_id = cq["message"]["chat"]["id"]
            message_id = cq["message"]["message_id"]
            callback_data = cq.get("data")
            
            state = user_states.get(user_id, "new_user")
            text = ""
            kb = None
            
            if state == "new_user":
                if callback_data == "action_start":
                    user_states[user_id] = "pet_type"
                    text = "Кто у вас живёт?"
                    kb = {"inline_keyboard": [[
                        {"text": " Кошка", "callback_data": "type_cat"},
                        {"text": "🐶 Собака", "callback_data": "type_dog"}
                    ]]}
                    
            elif state == "pet_type":
                if callback_data and callback_data.startswith("type_"):
                    user_states[user_id] = "completed"
                    pet_name = "Кошка" if "cat" in callback_data else "Собака"
                    text = f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен."
            
            if kb:
                payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "reply_markup": json.dumps(kb)}
                async with httpx.AsyncClient() as client:
                    await client.post(f"{BASE_URL}/editMessageText", json=payload)
            else:
                await send_message(chat_id, text)
                
        # Обработка текстовых сообщений (включая /start)
        elif "message" in data:
            msg = data["message"]
            user_id = msg["from"]["id"]
            chat_id = msg["chat"]["id"]
            text_msg = msg.get("text", "")
            
            if text_msg == "/start":
                user_states[user_id] = "new_user"
                await send_message(
                    chat_id, 
                    "Привет! 👋 Соберём календарь ухода.",
                    {"inline_keyboard": [[{"text": "Настроить календарь", "callback_data": "action_start"}]]}
                )
                
        return {"status": "ok"}
        
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
