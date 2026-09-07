from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder

app = FastAPI()
TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН_ОТ_BOTFATHER" 

@app.get("/")
async def root():
    return {"message": "Bot is alive!"}

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ApplicationBuilder().token(TOKEN).build())
    # Пока просто логируем, чтобы проверить запуск
    print(f"Received update from user: {update.effective_user.id if update.effective_user else 'Unknown'}")
    return {"status": "ok"}
