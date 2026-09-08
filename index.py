from fastapi import FastAPI, Request
import httpx
import json
import traceback

app = FastAPI()
TOKEN = "8850430202:AAFiMCG5AMnkZ1CZTEIne8cb-6J4CetJuhw"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

user_states = {}

async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/sendMessage", json=payload)
        if response.status_code != 200:
            raise Exception(f"Telegram API Error: {response.text}")

@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        
        # Проверяем, есть ли callback_query
        if "callback_query" not in data:
            return {"status": "ignored", "reason": "no_callback"}
            
        cq = data["callback_query"]
        user_id = cq["from"]["id"]
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]
        callback_data = cq.get("data")
        
        state = user_states.get(user_id, "new_user")
        text = ""
        kb = None
        
        # ЛОГИКА
        if state == "new_user":
            if callback_data == "action_start":
                user_states[user_id] = "pet_type"
                text = "Кто у вас живёт?"
                kb = {"inline_keyboard": [[
                    {"text": "🐱 Кошка", "callback_data": "type_cat"},
                    {"text": "🐶 Собака", "callback_data": "type_dog"}
                ]]}
            else:
                text = "Привет! 👋 Соберём календарь ухода."
                kb = {"inline_keyboard": [[{"text": "Настроить календарь", "callback_data": "action_start"}]]}
                
        elif state == "pet_type":
            if callback_data and callback_data.startswith("type_"):
                user_states[user_id] = "completed"
                pet_name = "Кошка" if "cat" in callback_data else "Собака"
                text = f"Отлично! {pet_name} добавлена ✅\nБазовый уход настроен."
        
        # ОТПРАВКА
        if kb:
            # Редактируем сообщение с кнопками
            payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "reply_markup": json.dumps(kb)}
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{BASE_URL}/editMessageText", json=payload)
                if resp.status_code != 200:
                    raise Exception(f"Edit Error: {resp.text}")
        else:
            await send_message(chat_id, text)
            
        return {"status": "ok"}
        
    except Exception as e:
        # ВАЖНО: Возвращаем ошибку в теле ответа, чтобы Vercel её показал
        error_trace = traceback.format_exc()
        print(f"ERROR: {error_trace}") 
        return {"status": "error", "message": str(e), "trace": error_trace}

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}
