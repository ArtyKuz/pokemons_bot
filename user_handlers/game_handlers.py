import random
import sqlite3

import asyncpg
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from services.classes import User, Pokemon
from services.services import get_data, evolution_pokemon, start_fortune, buy_in_shop, \
    get_pokemons_for_first_select, get_description
from lexicon.lexicon import LEXICON

# base = sqlite3.connect('Pokemon.db')
# cur = base.cursor()
# names_pokemons = [i[0] for i in cur.execute('SELECT Name FROM Pokemons').fetchall()]
# base.close()


async def start_game(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    await FSMPokemon.game.set()
    user = User(callback.from_user.id)
    if not await user.check_user(conn):
        await user.add_user_in_db(callback.from_user.username, conn)
        await callback.message.edit_text(f'{LEXICON["start_new_game"]}',
                                         reply_markup=create_inline_kb(1, 'Выбор покемонов'))
    elif await user.count_pokemons(conn) < 3:
        await callback.message.edit_text(f'{LEXICON["start_new_game"]}',
                                         reply_markup=create_inline_kb(1, 'Выбор покемонов'))
    else:
        await callback.message.answer(f'{LEXICON["start_game"]}', reply_markup=create_inline_kb(2,
                                                                                                'Охота на Покемонов 🎯',
                                                                                                'Лига Покемонов 🏆',
                                                                                                'Мои покемоны',
                                                                                                'Рюкзак 🎒',
                                                                                                'Магазин 🛍',
                                                                                                'Колесо Фортуны 🎰',
                                                                                                'Выход из игры ❌'))


async def start_first_select(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await FSMPokemon.first_select.set()
    async with state.proxy() as data:
        data['first_select'] = await get_pokemons_for_first_select(conn)
    await callback.message.edit_text('Сделай свой выбор!',
                                     reply_markup=create_inline_kb(2, *data['first_select']))


async def first_select(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer(f'Поздравляю! Теперь {callback.data} ваш покемон!', show_alert=True)
    async with state.proxy() as data:
        user = User(callback.from_user.id)
        await user.add_pokemon(callback.data, conn)
        if await user.count_pokemons(conn) < 3:
            data['first_select'] = data['first_select'] - {callback.data}
            await callback.message.edit_text('Выбирайте дальше!',
                                             reply_markup=create_inline_kb(2, *data['first_select']))
        else:
            keyboard = create_inline_kb(1, 'Мои покемоны', 'Начать игру')
            await callback.message.edit_text('Поздравляю! Вы выбрали 3 покемонов, теперь вы можете '
                                             'посмотреть ваших покемонов либо начать игру', reply_markup=keyboard)
            await FSMPokemon.game.set()


# Просмотр списка личных покемонов
async def watch_person_pokemons(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    user_pokemons = await User(callback.from_user.id).get_pokemons(conn)
    await callback.message.answer('Ваши покемоны!', reply_markup=create_inline_kb(2, *user_pokemons,
                                                                                  'Продолжить игру 🔄'))


# Просмотр информации о личном покемоне
async def description_person_pokemon(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    async with state.proxy() as data:
        data['evolution'] = callback.data
    image, description = await get_description(callback.data, conn, full=False, user_id=callback.from_user.id)
    await callback.message.answer_photo(image, caption=description,
                                        reply_markup=create_inline_kb(1, 'Эволюционировать покемона 🌀',
                                                                      'Мои покемоны', 'Продолжить игру 🔄'))


# Хэндлер для эволюции покемонов
async def evolution_pokemon_handler(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    async with state.proxy() as data:
        ev = await evolution_pokemon(pokemon=data['evolution'], user_id=callback.from_user.id, conn=conn)
    if type(ev) == int and ev == 0:
        await callback.message.answer(f'⚠ К сожалению, ваш покемон не имеет эволюций, попробуйте эволюционировать '
                                      f'другого покемона!',
                                      reply_markup=create_inline_kb(1, 'Мои покемоны', 'Продолжить игру 🔄'))
    elif ev == 'max':
        await callback.message.answer(f'⚠ К сожалению, ваш покемон уже достиг наивысшей формы, '
                                      f'попробуйте эволюционировать другого покемона!',
                                      reply_markup=create_inline_kb(1, 'Мои покемоны', 'Продолжить игру 🔄'))
    elif not ev:
        await callback.message.answer('⚠ К сожалению в данный момент вы не можете эволюционировать данного'
                                      ' покемона, так как у вас нет ни одного <b>камня эволюции.</b>',
                                      reply_markup=create_inline_kb(1, 'Мои покемоны', 'Продолжить игру 🔄'))
    else:
        await callback.message.answer(f'Поздравляю 🎉🎉🎉\nЭволюция прошла успешно ✅\n{data["evolution"]} '
                                      f'эволюционировал в <b>{ev}!</b>',
                                      reply_markup=create_inline_kb(1, 'Мои покемоны', 'Продолжить игру 🔄'))


async def wheel_of_fortune(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    current_date = callback.message.date.date()
    date_fortune = await conn.fetchval('SELECT date_fortune FROM users WHERE user_id = $1', callback.from_user.id)
    if date_fortune != current_date:
        await conn.execute('UPDATE users SET date_fortune = $1, fortune_attempts = 1 WHERE user_id = $2',
                           current_date, callback.from_user.id)

    await callback.message.answer(LEXICON['wheel_Fortune'],
                                  reply_markup=create_inline_kb(1, 'Крутить колесо!', 'Вернуться в главное меню'))


async def spin_wheel_fortune(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    select_fortune = await start_fortune(callback.from_user.id, conn)
    if select_fortune == 'eat':
        await callback.message.edit_text('Сегодня вам досталась: <b>Еда для усиления покемонов</b> 🍔',
                                         reply_markup=create_inline_kb(1, 'Рюкзак 🎒', 'Магазин 🛍',
                                                                       'Вернуться в главное меню'))
    elif type(select_fortune) == int:
        await callback.message.edit_text(f'Вам выпало: <b>{select_fortune} монет</b> 💰',
                                         reply_markup=create_inline_kb(1, 'Рюкзак 🎒', 'Магазин 🛍',
                                                                       'Вернуться в главное меню'))
    elif select_fortune == 'evolution_stone':
        await callback.message.edit_text(f'Сегодня вам крупно повезло! Вам выпал - <b>Камень эволюции!</b> 💎',
                                         reply_markup=create_inline_kb(1, 'Рюкзак 🎒', 'Магазин 🛍',
                                                                       'Вернуться в главное меню'))
    else:
        await callback.message.edit_text('Крутить <b>Колесо Фортуны</b> можно только 1 раз в день! Попробуйте завтра!',
                                         reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def backpack(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    coins, eat, stone, icons = await User(callback.from_user.id).get_backpack(conn=conn)
    await callback.message.answer(f'В данный момент у вас имеется:\n\n'
                                  f'🔹 монет - <b>{coins}</b> 💰\n🔹 порции еды - <b>{eat}</b> 🍔\n'
                                  f'🔹 Камней эволюции - <b>{stone}</b> 💎\n'
                                  f'🔹 Значки:\n{icons}',
                                  reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def shop_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('<b>Добро пожаловать в магазин!</b> Здесь вы можете купить:\n\n'
                                  '- Еда для усиления покемона 🍔 - стоимость 50 монет 💰\n'
                                  '- Камень эволюции 💎 - стоимость 100 монет 💰.',
                                  reply_markup=create_inline_kb(1, **{'Купить 🍔 за 50 💰': 'eat',
                                                                      'Купить 💎 за 100 💰': 'evolution_stone',
                                                                      'Вернуться в главное меню': 'Вернуться в главное '
                                                                                                  'меню'}))


async def shopping(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    menu = {'eat': 'Еда для усиления покемона 🍔',
            'evolution_stone': 'Камень эволюции 💎'}
    if await buy_in_shop(callback.data, callback.from_user.id, conn):
        await callback.message.answer(f'Вы приобрели - <b>{menu[callback.data]}!</b>',
                                      reply_markup=create_inline_kb(1, 'Рюкзак 🎒', 'Продолжить покупки',
                                                                    'Вернуться в главное меню'))
    else:
        await callback.message.answer('К сожалению у вас не хватает монет для приобретения данного товара.',
                                      reply_markup=create_inline_kb(1, 'Продолжить покупки',
                                                                    'Вернуться в главное меню'))


def register_game_handlers(dp: Dispatcher, names_pokemons):
    dp.register_callback_query_handler(start_game, text=['ИГРА 🎲', 'Продолжить игру 🔄', 'Начать игру',
                                                         'Вернуться в главное меню'])
    dp.register_callback_query_handler(start_game, text=['ИГРА 🎲', 'Продолжить игру 🔄', 'Начать игру',
                                                         'Вернуться в главное меню'],
                                       state=(FSMPokemon.game, FSMPokemon.hunting, FSMPokemon.replace_pokemon,
                                              FSMPokemon.pokemon_league))
    dp.register_callback_query_handler(start_first_select, text='Выбор покемонов', state=FSMPokemon.game)
    dp.register_callback_query_handler(first_select, text=names_pokemons, state=FSMPokemon.first_select)
    dp.register_callback_query_handler(watch_person_pokemons, text='Мои покемоны', state=FSMPokemon.game)
    dp.register_callback_query_handler(description_person_pokemon, text=names_pokemons, state=FSMPokemon.game)
    dp.register_callback_query_handler(evolution_pokemon_handler, text='Эволюционировать покемона 🌀',
                                       state=FSMPokemon.game)
    dp.register_callback_query_handler(wheel_of_fortune, text='Колесо Фортуны 🎰', state=FSMPokemon.game)
    dp.register_callback_query_handler(spin_wheel_fortune, text='Крутить колесо!', state=FSMPokemon.game)
    dp.register_callback_query_handler(backpack, text='Рюкзак 🎒', state=FSMPokemon.game)
    dp.register_callback_query_handler(shop_menu, text=['Магазин 🛍', 'Продолжить покупки'], state=FSMPokemon.game)
    dp.register_callback_query_handler(shopping, text=['eat', 'evolution_stone'],
                                       state=FSMPokemon.game)
