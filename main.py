import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Вставьте ваш токен от @BotFather
TOKEN = "8872574310:AAHzJrf6mHjHQns0ZQmIvz8mdpzCUx2WJf0"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)


# Состояния для пошагового ввода данных
class CourierForm(StatesGroup):
  stops = State()
  apm = State()
  picked_up = State()
  time_start = State()
  time_end = State()


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
  await state.clear()
  await message.answer(
      "Привет! Я бот для расчета зарплаты курьера.\n\n"
      "Давай посчитаем смену. Введи **количество стопов** за день:"
  )
  await state.set_state(CourierForm.stops)


# Шаг 1: Стопы
@dp.message(CourierForm.stops, F.text)
async def process_stops(message: types.Message, state: FSMContext):
  try:
    stops = int(message.text)
    if stops < 0:
      raise ValueError
    await state.update_data(stops=stops)
    await message.answer(
        "Отлично! Теперь введи **количество доставленных посылок на APM/PUDO**:"
    )
    await state.set_state(CourierForm.apm)
  except ValueError:
    await message.answer(
        "Пожалуйста, введи целое положительное число стопов."
    )


# Шаг 2: APM / PUDO
@dp.message(CourierForm.apm, F.text)
async def process_apm(message: types.Message, state: FSMContext):
  try:
    apm = int(message.text)
    if apm < 0:
      raise ValueError
    await state.update_data(apm=apm)
    await message.answer("Сколько посылок было **отобрано** (pick-up)?")
    await state.set_state(CourierForm.picked_up)
  except ValueError:
    await message.answer("Пожалуйста, введи число.")


# Шаг 3: Отобранные посылки
@dp.message(CourierForm.picked_up, F.text)
async def process_picked_up(message: types.Message, state: FSMContext):
  try:
    picked_up = int(message.text)
    if picked_up < 0:
      raise ValueError
    await state.update_data(picked_up=picked_up)
    await message.answer(
        "Во сколько ты **начал** работу? (введи в формате ЧЧ:ММ, например,"
        " 08:30):"
    )
    await state.set_state(CourierForm.time_start)
  except ValueError:
    await message.answer("Пожалуйста, введи число.")


# Шаг 4: Время начала
@dp.message(CourierForm.time_start, F.text)
async def process_time_start(message: types.Message, state: FSMContext):
  try:
    datetime.strptime(message.text, "%H:%M")
    await state.update_data(time_start=message.text)
    await message.answer(
        "Во сколько ты **закончил** работу? (введи в формате ЧЧ:ММ, например,"
        " 17:45):"
    )
    await state.set_state(CourierForm.time_end)
  except ValueError:
    await message.answer("Неверный формат времени. Введи в формате ЧЧ:ММ:")


# Шаг 5: Время окончания и финальный расчет
@dp.message(CourierForm.time_end, F.text)
async def process_time_end(message: types.Message, state: FSMContext):
  try:
    time_end = message.text
    datetime.strptime(time_end, "%H:%M")
    data = await state.get_data()

    stops = data["stops"]
    apm = data["apm"]
    picked_up = data["picked_up"]
    time_start = data["time_start"]

    # Расчет ставки за стопы
    if stops <= 74:
      stops_pay = 240
    else:
      # Каждые 10 стопов сверх 74 дают +30зл (начиная с 75)
      extra_steps = (stops - 75) // 10
      stops_pay = 270 + (extra_steps * 30)

    # Доплаты
    apm_pay = apm * 0.10
    picked_pay = picked_up * 0.10
    total_pay = stops_pay + apm_pay + picked_pay

    # Расчет времени
    FMT = "%H:%M"
    t1 = datetime.strptime(time_start, FMT)
    t2 = datetime.strptime(time_end, FMT)

    # Обработка перехода через полночь (если актуально)
    if t2 < t1:
      from datetime import timedelta

      t2 += timedelta(days=1)

    duration = t2 - t1
    hours = duration.seconds / 3600
    hourly_rate = total_pay / hours if hours > 0 else 0

    # Формируем отчет
    report = (
        "📊 **Итог за смену:**\n\n"
        f"📍 Стопы: {stops} шт. — **{stops_pay:.2f} зл**\n"
        f"📦 APM/PUDO: {apm} шт. — **{apm_pay:.2f} зл**\n"
        f"📥 Отобрано: {picked_up} шт. — **{picked_pay:.2f} зл**\n\n"
        f"⏱ Время работы: с {time_start} до {time_end} "
        f"(_~{hours:.1f} ч_)\n"
        f"💰 **Общий доход:** **{total_pay:.2f} зл**\n"
        f"⚡️ В час: **{hourly_rate:.2f} зл/ч**\n\n"
        "Чтобы посчитать новый день, просто отправь /start"
    )

    await message.answer(report, parse_mode="Markdown")
    await state.clear()

  except ValueError:
    await message.answer("Неверный формат времени. Введи в формате ЧЧ:ММ:")


if __name__ == "__main__":
  import asyncio

  asyncio.run(dp.start_polling(bot))