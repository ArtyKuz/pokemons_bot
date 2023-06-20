import sqlite3

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from services.services import get_description, get_best_pokemons
from lexicon.lexicon import LEXICON

base = sqlite3.connect('Pokemon.db')
cur = base.cursor()
types_pok = [i[0] for i in cur.execute('SELECT Type FROM Pokemons').fetchall()]
names_pokemons = [i[0] for i in cur.execute('SELECT Name FROM Pokemons').fetchall()]
base.close()


async def start_pokedeks(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(f'{LEXICON["start_pokedeks"]}', reply_markup=create_inline_kb(1, 'Типы покемонов',
                                                                                                   'Лучшие покемоны',
                                                                                                   'Выход из ПОКЕДЕКСА ❌'))
    await FSMPokemon.pokedeks.set()


async def types_pokemons(callback: CallbackQuery):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        pokemon_types = sorted(i[0] for i in cur.execute('SELECT DISTINCT Type FROM Pokemons').fetchall())
        await callback.message.answer('Выбирай тип покемона!',
                                      reply_markup=create_inline_kb(2, *pokemon_types, 'Выход в меню Покедекса 📖'))


async def one_type_pokemons(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        pokemons = [i[0] for i in cur.execute(f'SELECT Name FROM Pokemons WHERE Type LIKE '
                                          f'"{callback.data}" ORDER BY Эволюция').fetchall()]
        await callback.message.answer(f'К типу <b>{callback.data}</b> относятся следующие покемоны:',
                                      reply_markup=create_inline_kb(2, *pokemons))


async def description_pokemon(callback: CallbackQuery):
    await callback.answer()
    image, description = get_description(callback.data)
    await callback.message.answer_photo(image, caption=description,
                                        reply_markup=create_inline_kb(1, 'Типы покемонов', 'Выход в меню Покедекса 📖'))


async def best_pokemons(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Здесь вы можете посмотреть 10-ки лучших покемонов по различным характеристикам:',
                                     reply_markup=create_inline_kb(1, 'Лучшие покемоны по сумме хар-к',
                                                                   'Лучшие покемоны по Здоровью',
                                                                   'Лучшие покемоны по Атаке',
                                                                   'Лучшие покемоны по Защите',
                                                                   'Выход в меню Покедекса 📖'))


async def show_best_pokemons(callback: CallbackQuery):
    await callback.answer()
    best_pokemons = get_best_pokemons(callback.data)
    await callback.message.edit_text(f'{best_pokemons}', reply_markup=create_inline_kb(1, 'Лучшие покемоны',
                                                                           'Выход в меню Покедекса 📖'))


async def exit_pokedeks(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Добро пожаловать в мир Покемонов!',
                                  reply_markup=create_inline_kb(1, 'ИГРА 🎲', 'ПОКЕДЕКС 📖'))
    await state.finish()


def register_pokedeks_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(start_pokedeks, text='ПОКЕДЕКС 📖')
    dp.register_callback_query_handler(start_pokedeks, text=['ПОКЕДЕКС 📖', 'Выход в меню Покедекса 📖'],
                                       state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(types_pokemons, text='Типы покемонов', state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(one_type_pokemons, text=types_pok, state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(description_pokemon, text=names_pokemons, state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(best_pokemons, text='Лучшие покемоны', state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(show_best_pokemons, text=['Лучшие покемоны по сумме хар-к',
                                                                 'Лучшие покемоны по Здоровью',
                                                                 'Лучшие покемоны по Атаке',
                                                                 'Лучшие покемоны по Защите'],
                                       state=FSMPokemon.pokedeks)
    dp.register_callback_query_handler(exit_pokedeks, text='Выход из ПОКЕДЕКСА ❌', state=FSMPokemon.pokedeks)
