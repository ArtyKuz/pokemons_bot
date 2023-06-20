import random
import sqlite3
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from lexicon.lexicon import LEXICON
from services.services import get_description, get_characteristic_for_fight, get_fight, update_icons, \
    get_text_for_icons, enhance_pokemon, get_text_for_fight

base = sqlite3.connect('Pokemon.db')
cur = base.cursor()
names_pokemons = [i[0] for i in cur.execute('SELECT Name FROM Pokemons').fetchall()]
base.close()

icons = {1: 'Завоевать Каменный значок 🔘', 2: 'Завоевать Каскадный значок 💧', 3: 'Завоевать Электрический значок ⚡',
         4: 'Завоевать Психический значок 🧿', 5: 'Завоевать Радужный значок 🌈', 6: 'Завоевать Сердечный значок 💜',
         7: 'Завоевать Вулканический значок 🌋', 8: 'Завоевать Земляной значок 🟤'}


async def start_pokemon_league(callback: CallbackQuery, state: FSMContext):
    await FSMPokemon.pokemon_league.set()
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if len(cur.execute('SELECT pokemons FROM Users WHERE id = {}'.format(callback.from_user.id)).fetchone()[
                   0].split()) < 7:
            await callback.message.answer('Для участия в Лиге Покемонов у вас должно быть не менее 7 покемонов. '
                                          'Поймать покемонов можно в режиме <b>"Охота на покемонов"</b>.',
                                          reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))
        else:
            point = cur.execute(f'SELECT point FROM Users WHERE id = {callback.from_user.id}').fetchone()[0]
            await callback.message.answer(f'{get_text_for_icons(point, LEXICON["start_pokemon_league"])}',
                                          reply_markup=create_inline_kb(1, icons[point], 'Вернуться в главное меню'))


async def pre_start_fight(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        async with state.proxy() as data:
            data['icon'] = ' '.join(callback.data.split()[1:])
            data['level'] = 1
            data['my_point'] = 0
            data['enemy_point'] = 0
            data['all_enemy_pokemons']: list = cur.execute(f'SELECT pokemons FROM Icons WHERE point = ('
                                                           f'SELECT point FROM Users WHERE id = {callback.from_user.id})').fetchone() \
                [0].split()
            data['my_pokemons']: set = set(cur.execute(f'SELECT pokemons FROM Users WHERE id = '
                                                       f'{callback.from_user.id}').fetchone()[0].split())
            await callback.message.answer(f'Для того чтобы завоевать {data["icon"]} вам придется сразиться с:\n'
                                          f'- <b>{data["all_enemy_pokemons"][0]}</b>\n'
                                          f'- <b>{data["all_enemy_pokemons"][1]}</b>\n'
                                          f'- <b>{data["all_enemy_pokemons"][2]}</b>\n\n'
                                          f'Сражение продолжается до 2-х побед!',
                                          reply_markup=create_inline_kb(1, 'Начать сражение!',
                                                                        'Вернуться в главное меню'))


async def select_pokemon(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    async with state.proxy() as data:
        data['enemy_pokemon']: str = random.sample(data['all_enemy_pokemons'], k=1)[0]
        data['all_enemy_pokemons']: set = set(data['all_enemy_pokemons']) - {data['enemy_pokemon']}
        image, description = get_description(data['enemy_pokemon'], full=False)
        await callback.message.answer_photo(image, caption=f'{description}\n\nВыберите своего покемона!',
                                            reply_markup=create_inline_kb(2, *data['my_pokemons']))


async def start_fight_for_icons(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['my_pokemons'] = data['my_pokemons'] - {callback.data}
        data['enemy_pokemon'], data['my_pokemon'], data['eat'] = get_characteristic_for_fight(data['enemy_pokemon'],
                                                                                              callback.data,
                                                                                              callback.from_user.id)
        data['dice'] = random.randrange(0, 2)
        if data['dice']:
            await callback.answer('🎲 Ваш ход будет первым!', show_alert=True)
        else:
            await callback.answer(f'🎲 {data["enemy_pokemon"]["Name"]} будет атаковать первым!', show_alert=True)
        await callback.message.answer(
            f'<b>{data["level"]} - Раунд!</b> 💥💥💥\n\n<b>{data["my_pokemon"]["Name"]}</b> против <b>{data["enemy_pokemon"]["Name"]}</b>!',
            reply_markup=create_inline_kb(1, 'Начать бой!'))


async def fight_for_icons(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if 'Усилить покемона' in callback.data:
            data['eat'] -= 1
            data["my_pokemon"] = enhance_pokemon(data["my_pokemon"], callback.from_user.id)
            await callback.message.edit_text(get_text_for_fight(data['dice'], data["my_pokemon"], data["enemy_pokemon"],
                                                                enhance=True),
                                             reply_markup=create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))
        elif callback.data == 'Сдаться 🏳️':
            data['enemy_point'] += 1
            if data['my_point'] < 2 and data['enemy_point'] < 2:
                data['level'] += 1
                await callback.message.edit_text(f'Победа присуждена <b>{data["enemy_pokemon"]["Name"]}!</b>',
                                                 reply_markup=create_inline_kb(1, 'Продолжить',
                                                                               'Вернуться в главное меню'))
            else:
                await callback.message.edit_text('К сожалению вы проиграли!',
                                                 reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                               'Вернуться в главное меню'))
        # Ход игрока
        elif data['dice']:
            dice_attack, dice_defence, damage, data['enemy_pokemon'] = get_fight(1, data['enemy_pokemon'],
                                                                                 data['my_pokemon'])
            await callback.answer(f'{data["my_pokemon"]["Name"]} - {dice_attack} 🎲 (Атака)\n\n'
                                  f'{data["enemy_pokemon"]["Name"]} - {dice_defence} 🎲 (Защита)', show_alert=True)
            if data['enemy_pokemon']['HP'] > 0:
                await callback.message.edit_text(
                    get_text_for_fight(data['dice'], data["my_pokemon"], data["enemy_pokemon"],
                                       damage=damage),
                    reply_markup=create_inline_kb(1, 'Ход противника', 'Сдаться 🏳️'))
                data['dice'] -= 1
            else:
                data['my_point'] += 1
                if data['my_point'] < 2 and data['enemy_point'] < 2:
                    data['level'] += 1
                    await callback.message.edit_text(
                        f'<b>{data["my_pokemon"]["Name"]}</b> победил!',
                        reply_markup=create_inline_kb(1, 'Продолжить', 'Вернуться в главное меню'))
                else:
                    if data['my_point'] > data['enemy_point']:
                        update_icons(callback.from_user.id, data["icon"])
                        await callback.message.edit_text(f'Ура! Вы выиграли <b>{data["icon"]}!</b>',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))
                    else:
                        await callback.message.edit_text('К сожалению вы проиграли!',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))

        # Ход противника (бота)
        else:
            dice_attack, dice_defence, damage, data['my_pokemon'] = get_fight(0, data['enemy_pokemon'],
                                                                              data['my_pokemon'])
            await callback.answer(f'{data["enemy_pokemon"]["Name"]} - {dice_attack} 🎲 (Атака)\n\n'
                                  f'{data["my_pokemon"]["Name"]} - {dice_defence} 🎲 (Защита)', show_alert=True)
            if data['my_pokemon']['HP'] > 0:
                await callback.message.edit_text(
                    get_text_for_fight(data['dice'], data["my_pokemon"], data["enemy_pokemon"],
                                       damage=damage),
                    reply_markup=create_inline_kb(1, 'Атаковать!',
                                                  f'Усилить покемона ({data["eat"]} 🍔)',
                                                  'Сдаться 🏳️') if data['eat'] else
                    create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))
                data['dice'] += 1
            else:
                data['enemy_point'] += 1
                if data['my_point'] < 2 and data['enemy_point'] < 2:
                    data['level'] += 1
                    await callback.message.edit_text(f'<b>{data["enemy_pokemon"]["Name"]}</b> победил!',
                                                     reply_markup=create_inline_kb(1, 'Продолжить',
                                                                                   'Вернуться в главное меню'))
                else:
                    if data['my_point'] > data['enemy_point']:
                        update_icons(callback.from_user.id, data["icon"])
                        await callback.message.edit_text(f'Ура! Вы выиграли <b>{data["icon"]}!</b>',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))
                    else:
                        await callback.message.edit_text('К сожалению вы проиграли!',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))


def register_pokemon_league_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(start_pokemon_league, text='Лига Покемонов 🏆', state=(FSMPokemon.game,
                                                                                             FSMPokemon.pokemon_league))
    dp.register_callback_query_handler(pre_start_fight, text=list(icons.values()), state=FSMPokemon.pokemon_league)
    dp.register_callback_query_handler(select_pokemon, text=['Начать сражение!',
                                                             'Продолжить'], state=FSMPokemon.pokemon_league)
    dp.register_callback_query_handler(start_fight_for_icons, text=names_pokemons, state=FSMPokemon.pokemon_league)
    dp.register_callback_query_handler(fight_for_icons, text=['Начать бой!',
                                                              'Атаковать!',
                                                              'Ход противника',
                                                              'Сдаться 🏳️'], state=FSMPokemon.pokemon_league)
    dp.register_callback_query_handler(fight_for_icons, Text(startswith='Усилить покемона'),
                                       state=FSMPokemon.pokemon_league)
