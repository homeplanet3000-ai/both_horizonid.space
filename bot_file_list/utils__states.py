from aiogram.fsm.state import State, StatesGroup

class BuySubscription(StatesGroup):
    choosing_tariff = State()      # Пользователь выбирает тариф
    waiting_for_payment = State()  # Пользователь получил счет и мы ждем оплату

class Broadcast(StatesGroup):
    typing_message = State()       # Админ пишет сообщение для рассылки
    confirming = State()           # Админ подтверждает рассылку
