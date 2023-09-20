import asyncpg
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from lexicon.lexicon import LEXICON
from services.services import get_best_pokemons, get_description


async def start_pokedeks(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(f'{LEXICON["start_pokedeks"]}', reply_markup=create_inline_kb(1, 'Типы покемонов',
                                                                                                'Лучшие покемоны',
                                                                                                'Выход из ПОКЕДЕКСА ❌'))
    await FSMPokemon.pokedeks.set()


async def types_pokemons(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    pokemon_types = sorted(i['name_type'] for i in await conn.fetch('SELECT name_type FROM types_pokemons'))
    await callback.message.answer('Выбирай тип покемона!',
                                  reply_markup=create_inline_kb(2, *pokemon_types, 'Выход в меню Покедекса 📖'))


async def one_type_pokemons(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    pokemons = [i['pokemon_name'] for i in await conn.fetch(f'SELECT pokemon_name FROM pokemons JOIN types_pokemons '
                                                            f'ON pokemons.type_pokemon = types_pokemons.type_id '
                                                            f'WHERE name_type = $1 ORDER BY evolution_group',
                                                            callback.data)]
    await callback.message.answer(f'К типу <b>{callback.data}</b> относятся следующие покемоны:',
                                  reply_markup=create_inline_kb(2, *pokemons))


async def description_pokemon(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    image, description = await get_description(callback.data, conn)
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


async def show_best_pokemons(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    best_pokemons = await get_best_pokemons(callback.data, conn)
    await callback.message.edit_text(f'{best_pokemons}', reply_markup=create_inline_kb(1, 'Лучшие покемоны',
                                                                                       'Выход в меню Покедекса 📖'))


async def exit_pokedeks(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Добро пожаловать в мир Покемонов!',
                                  reply_markup=create_inline_kb(1, 'ИГРА 🎲', 'ПОКЕДЕКС 📖'))
    await state.finish()


def register_pokedeks_handlers(dp: Dispatcher, types_pok, names_pokemons):
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
