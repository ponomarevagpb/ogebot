import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import os

# ---------- ЗАМЕНИ ЭТИ ДВЕ СТРОКИ ----------
API_TOKEN = "8512097138:AAFGZxwmX94iExF19ZbYTsvknJ6HkqbVeWs"
USERNAME = "Ponga"
# -------------------------------------------

WEBHOOK_HOST = f"https://{USERNAME}.pythonanywhere.com"
WEBHOOK_PATH = "/webhook"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "tasks.json"), "r", encoding="utf-8") as f:
    TASKS = json.load(f)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class TaskState(StatesGroup):
    waiting_text_answer = State()

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎲 Получить задание", callback_data="get_task")]
])

def get_random_task():
    return random.choice(TASKS)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот-тренажёр. Нажми кнопку, чтобы получить задание.",
        reply_markup=main_kb
    )

@dp.callback_query(F.data == "get_task")
async def send_task(callback: types.CallbackQuery, state: FSMContext):
    task = get_random_task()
    await state.update_data(current_task=task)

    # Отправляем текст задания
    await callback.message.answer(task["question"])

    if task["type"] == "choice" and task["choices"]:
        buttons = []
        for ch in task["choices"]:
            buttons.append([InlineKeyboardButton(text=str(ch), callback_data=f"answer_{ch}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer("Выбери вариант ответа:", reply_markup=kb)
    else:
        await callback.message.answer("✏️ Введи ответ текстом:")
        await state.set_state(TaskState.waiting_text_answer)
    await callback.answer()

@dp.callback_query(F.data.startswith("answer_"))
async def handle_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task = data.get("current_task")
    if not task:
        await callback.answer("Сначала получи задание.")
        return
    user_choice = callback.data.split("_", 1)[1]
    if user_choice.strip().lower() == task["correct_answer"].strip().lower():
        await callback.message.answer("✅ Верно!")
    else:
        await callback.message.answer(
            f"❌ Неверно. Правильный ответ: {task['correct_answer']}\n"
            f"📘 Объяснение: {task.get('explanation', 'пока нет')}"
        )
    await callback.message.answer("Продолжим?", reply_markup=main_kb)
    await state.clear()
    await callback.answer()

@dp.message(StateFilter(TaskState.waiting_text_answer))
async def handle_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task = data.get("current_task")
    if not task:
        await message.answer("Сначала получи задание.")
        return
    user_answer = message.text.strip().lower()
    if user_answer == task["correct_answer"].strip().lower():
        await message.answer("✅ Правильно!")
    else:
        await message.answer(
            f"❌ Ошибка. Правильный ответ: {task['correct_answer']}\n"
            f"📘 Объяснение: {task.get('explanation', 'пока нет')}"
        )
    await message.answer("Следующее задание?", reply_markup=main_kb)
    await state.clear()

# Webhook setup
async def on_startup(bot: Bot):
    await bot.set_webhook(f"{WEBHOOK_HOST}{WEBHOOK_PATH}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()