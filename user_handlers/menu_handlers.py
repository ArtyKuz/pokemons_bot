from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from lexicon.lexicon import LEXICON


async def start(message: Message):
    await message.answer(f'{LEXICON["start"]}',
                         reply_markup=create_inline_kb(1, 'ИГРА 🎲', 'ПОКЕДЕКС 📖'))


async def back_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Добро пожаловать в мир Покемонов!',
                                  reply_markup=create_inline_kb(1, 'ИГРА 🎲', 'ПОКЕДЕКС 📖'))
    await state.finish()


def register_menu_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands='start')
    dp.register_message_handler(start, commands='start', state=(FSMPokemon.game, FSMPokemon.pokemon_league))
    dp.register_callback_query_handler(back_start, text='Выход из игры ❌', state=FSMPokemon.game)
