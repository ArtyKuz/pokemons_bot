import random
import sqlite3

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from services.services import get_description, get_characteristic_for_fight, get_fight, evolution_pokemon, \
    start_fortune, buy_in_shop
from lexicon.lexicon import LEXICON

base = sqlite3.connect('Pokemon.db')
cur = base.cursor()
names_pokemons = [i[0] for i in cur.execute('SELECT Name FROM Pokemons').fetchall()]
base.close()


async def start_game(callback: CallbackQuery):
    await callback.answer()
    await FSMPokemon.game.set()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if cur.execute('SELECT * FROM Users WHERE id = {}'.format(callback.from_user.id)).fetchone() is None:
            cur.execute(
                f"INSERT INTO Users (id, user_name) VALUES ({callback.from_user.id}, '{callback.from_user.first_name} "
                f"{callback.from_user.last_name}')")
            base.commit()
            await callback.message.edit_text(f'{LEXICON["start_new_game"]}',
                                             reply_markup=create_inline_kb(1, 'Выбор покемонов'))

        elif cur.execute('SELECT pokemons FROM Users WHERE id = {}'.format(callback.from_user.id)).fetchone()[
            0] is None or \
                len(cur.execute('SELECT pokemons FROM Users WHERE id = {}'.format(callback.from_user.id)).fetchone()[
                        0].split()) < 3:
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


async def start_first_select(callback: CallbackQuery, state: FSMContext):
    await FSMPokemon.first_select.set()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        s = [i[0] for i in cur.execute(f'SELECT Name FROM Pokemons WHERE Level = 1 AND Type <> "Психический 😵‍💫"'
                                       f'AND Type <> "Призрак 👻"').fetchall()]
        pokemons = random.sample(s, k=10)
        async with state.proxy() as data:
            data['first_select'] = set(pokemons)
    await callback.message.edit_text('Сделай свой выбор!',
                                     reply_markup=create_inline_kb(2, *pokemons))


async def first_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer(f'Поздравляю! Теперь {callback.data} ваш покемон!', show_alert=True)
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        ls_pok = cur.execute('SELECT pokemons FROM Users WHERE id = {}'.format(callback.from_user.id)).fetchone()[0]
        if ls_pok == None:
            cur.execute(
                "UPDATE Users SET pokemons = '{}' WHERE id = {}".format(callback.data, callback.from_user.id))
            base.commit()
            async with state.proxy() as data:
                data['first_select'] = data['first_select'] - {callback.data}
                await callback.message.edit_text('Выбирайте дальше!',
                                                 reply_markup=create_inline_kb(2, *data['first_select']))
        else:
            ls_pok += f' {callback.data}'
            cur.execute("UPDATE Users SET pokemons = '{}' WHERE id = {}".format(ls_pok, callback.from_user.id))
            base.commit()
            if len(ls_pok.split()) == 3:
                keyboard = create_inline_kb(1, 'Мои покемоны', 'Начать игру')
                await callback.message.edit_text('Поздравляю! Вы выбрали 3 покемонов, теперь вы можете '
                                                 'посмотреть ваших покемонов либо начать игру', reply_markup=keyboard)
                await FSMPokemon.game.set()
            else:
                async with state.proxy() as data:
                    data['first_select'] = data['first_select'] - {callback.data}
                    keyboard = create_inline_kb(2, *data['first_select'])
                    await callback.message.edit_text('Выбирайте дальше!', reply_markup=keyboard)


# Просмотр списка личных покемонов
async def watch_person_pokemons(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        s = cur.execute(f'SELECT pokemons FROM Users WHERE id = {callback.from_user.id}').fetchone()[0].split()
        await callback.message.answer('Ваши покемоны!', reply_markup=create_inline_kb(2, *s, 'Продолжить игру 🔄'))


# Просмотр информации о личном покемоне
async def description_person_pokemon(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    async with state.proxy() as data:
        data['evolution'] = callback.data
    image, description = get_description(callback.data, full=False)
    await callback.message.answer_photo(image, caption=description,
                                        reply_markup=create_inline_kb(1, 'Эволюционировать покемона 🌀',
                                                                      'Мои покемоны', 'Продолжить игру 🔄'))


# Хэндлер для эволюции покемонов
async def evolution_pokemon_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    async with state.proxy() as data:
        ev = evolution_pokemon(pokemon=data['evolution'], id=callback.from_user.id)
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


async def wheel_of_Fortune(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_date = callback.message.date.date().strftime('%d.%m.%Y')
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if cur.execute(f'SELECT date_fortune FROM Users WHERE id = {callback.from_user.id}').fetchone()[0] != user_date:
            cur.execute(
                f'UPDATE Users SET date_fortune = "{user_date}", wheel_of_Fortune = 1 WHERE id = {callback.from_user.id}')
            base.commit()
    await callback.message.answer(LEXICON['wheel_Fortune'],
                                  reply_markup=create_inline_kb(1, 'Крутить колесо!', 'Вернуться в главное меню'))


async def spin_wheel_fortune(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    select_fortune = start_fortune(callback.from_user.id)
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


async def backpack(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        coins, eat, stone, icons = cur.execute(f'SELECT coins, eat, evolution_stone, icons FROM Users WHERE id = '
                                        f'{callback.from_user.id}').fetchall()[0]
        await callback.message.answer(f'В данный момент у вас имеется:\n'
                                      f'🔹 монет - <b>{coins}</b> 💰\n🔹 порции еды - <b>{eat}</b> 🍔\n'
                                      f'🔹 Камней эволюции - <b>{stone}</b> 💎\n'
                                      f'🔹 Значки:\n{icons}',
                                      reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def shop_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer('Здесь вы можете купить:\n- Еда для усиления покемона 🍔 - стоимость 50 монет 💰\n'
                                  '- Камень эволюции 💎 - стоимость 100 монет 💰.',
                                  reply_markup=create_inline_kb(1, **{'Купить 🍔 за 50 💰': 'eat',
                                                                      'Купить 💎 за 100 💰': 'evolution_stone',
                                                                      'Вернуться в главное меню': 'Вернуться в главное '
                                                                                                  'меню'}))


async def shopping(callback: CallbackQuery):
    await callback.answer()
    menu = {'eat': 'Еда для усиления покемона 🍔', 'evolution_stone': 'Камень эволюции 💎'}
    if buy_in_shop(callback.data, callback.from_user.id):
        await callback.message.answer(f'Вы приобрели - <b>{menu[callback.data]}!</b>',
                                      reply_markup=create_inline_kb(1, 'Продолжить покупки',
                                                                    'Вернуться в главное меню'))
    else:
        await callback.message.answer('К сожалению у вас не хватает монет для приобретения данного товара.',
                                      reply_markup=create_inline_kb(1, 'Продолжить покупки',
                                                                    'Вернуться в главное меню'))


def register_game_handlers(dp: Dispatcher):
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
    dp.register_callback_query_handler(wheel_of_Fortune, text='Колесо Фортуны 🎰', state=FSMPokemon.game)
    dp.register_callback_query_handler(spin_wheel_fortune, text='Крутить колесо!', state=FSMPokemon.game)
    dp.register_callback_query_handler(backpack, text='Рюкзак 🎒', state=FSMPokemon.game)
    dp.register_callback_query_handler(shop_menu, text=['Магазин 🛍', 'Продолжить покупки'], state=FSMPokemon.game)
    dp.register_callback_query_handler(shopping, text=['eat', 'evolution_stone'],
                                       state=FSMPokemon.game)
