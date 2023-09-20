import random

import asyncpg
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery

from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from lexicon.lexicon import LEXICON
from services.classes import Pokemon, User
from services.services import (create_pokemon_for_fight, get_description,
                               get_fight, get_pokemons_icon,
                               get_text_for_fight, get_text_for_icons)

icons = {1: 'Завоевать Каменный значок 🔘', 2: 'Завоевать Каскадный значок 💧', 3: 'Завоевать Электрический значок ⚡',
         4: 'Завоевать Психический значок 🧿', 5: 'Завоевать Радужный значок 🌈', 6: 'Завоевать Сердечный значок 💜',
         7: 'Завоевать Вулканический значок 🌋', 8: 'Завоевать Земляной значок 🟤'}


async def start_pokemon_league(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await FSMPokemon.pokemon_league.set()
    await callback.answer()
    pokemons = await User(callback.from_user.id).get_pokemons(conn)
    if len(pokemons) < 7:
        await callback.message.answer('Для участия в Лиге Покемонов у вас должно быть не менее 7 покемонов.\n\n'
                                      'Поймать покемонов можно в режиме <b>"Охота на покемонов"</b>.',
                                      reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))
    else:
        async with state.proxy() as data:
            data['point'] = await conn.fetchval(f'SELECT points FROM users WHERE user_id = $1', callback.from_user.id)
            await callback.message.answer(f'{get_text_for_icons(data["point"], LEXICON["start_pokemon_league"])}',
                                          reply_markup=create_inline_kb(1, icons[data["point"]],
                                                                        'Вернуться в главное меню'))


async def pre_start_fight(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    async with state.proxy() as data:
        data['icon'] = ' '.join(callback.data.split()[1:])
        data['level'] = 1
        data['my_point'] = 0
        data['enemy_point'] = 0
        data['all_enemy_pokemons']: list = await get_pokemons_icon(data['point'], conn)
        pokemons = await User(callback.from_user.id).get_pokemons_for_fight(conn)
        if len(pokemons) >= 3:
            data['my_pokemons']: set = set(pokemons)
            await callback.message.answer(f'Для того чтобы завоевать {data["icon"]} вам придется сразиться с:\n'
                                          f'- <b>{data["all_enemy_pokemons"][0]}</b>\n'
                                          f'- <b>{data["all_enemy_pokemons"][1]}</b>\n'
                                          f'- <b>{data["all_enemy_pokemons"][2]}</b>\n\n'
                                          f'Сражение продолжается до 2-х побед!',
                                          reply_markup=create_inline_kb(1, 'Начать сражение!',
                                                                        'Вернуться в главное меню'))
        else:
            await callback.message.answer('Для участия в сражении за значок у вас должно быть не менее 3-х покемонов '
                                          'с энергией больше 0, подождите пока энергия ваших покемонов восстановится!',
                                          reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def select_pokemon(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await callback.answer()
    async with state.proxy() as data:
        enemy_pokemon = random.choice(list(data['all_enemy_pokemons']))
        data['enemy_pokemon']: Pokemon = await create_pokemon_for_fight(enemy_pokemon, conn)
        data['all_enemy_pokemons']: set = set(data['all_enemy_pokemons']) - {str(data['enemy_pokemon'])}
        image, description = await get_description(enemy_pokemon, conn, full=False)
        await callback.message.answer_photo(image, caption=f'{description}\n\nВыберите своего покемона!',
                                            reply_markup=create_inline_kb(2, *data['my_pokemons']))


async def start_fight_for_icons(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        data['my_pokemons'] = data['my_pokemons'] - {callback.data}
        user_pokemon = await create_pokemon_for_fight(callback.data, conn)
        enemy_pokemon = data['enemy_pokemon']
        data['user_pokemon'] = user_pokemon
        data['eat'] = await conn.fetchval(f'SELECT eat FROM users WHERE user_id = $1', callback.from_user.id)
        data['dice'] = random.randrange(0, 2)
        if data['dice']:
            await callback.answer('🎲 Ваш ход будет первым!', show_alert=True)
        else:
            await callback.answer(f'🎲 {enemy_pokemon} будет атаковать первым!', show_alert=True)
        await callback.message.answer(
            f'<b>{data["level"]} - Раунд!</b> 💥💥💥\n\n<b>{user_pokemon}</b> против <b>{enemy_pokemon}</b>!',
            reply_markup=create_inline_kb(1, 'Начать бой!'))


async def fight_for_icons(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        user_pokemon: Pokemon = data['user_pokemon']
        enemy_pokemon: Pokemon = data['enemy_pokemon']
        if 'Усилить покемона' in callback.data:
            data['eat'] -= 1
            data['my_pokemon'] = await user_pokemon.enhance(callback.from_user.id, conn)
            await callback.message.edit_text(get_text_for_fight(user_pokemon, enemy_pokemon, enhance=True),
                                             reply_markup=create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))
        elif callback.data == 'Сдаться 🏳️':
            await user_pokemon.drop_energy(callback.from_user.id, conn)
            data['enemy_point'] += 1
            if data['my_point'] < 2 and data['enemy_point'] < 2:
                data['level'] += 1
                await callback.message.edit_text(f'Победа присуждена <b>{enemy_pokemon}!</b>',
                                                 reply_markup=create_inline_kb(1, 'Продолжить',
                                                                               'Вернуться в главное меню'))
            else:
                await callback.message.edit_text('К сожалению вы проиграли!',
                                                 reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                               'Вернуться в главное меню'))
        # Ход игрока
        elif data['dice']:
            dice_attack, dice_defence, damage, enemy_pokemon = get_fight(user_pokemon, enemy_pokemon)
            data['enemy_pokemon'] = enemy_pokemon
            await callback.answer(f'{user_pokemon} - {dice_attack} 🎲 (Атака)\n\n'
                                  f'{enemy_pokemon} - {dice_defence} 🎲 (Защита)', show_alert=True)
            if enemy_pokemon.hp > 0:
                await callback.message.edit_text(
                    get_text_for_fight(user_pokemon, enemy_pokemon, dice=data['dice'], damage=damage),
                    reply_markup=create_inline_kb(1, 'Ход противника', 'Сдаться 🏳️'))
                data['dice'] -= 1
            else:
                data['my_point'] += 1
                if data['my_point'] < 2 and data['enemy_point'] < 2:
                    data['level'] += 1
                    await callback.message.edit_text(
                        f'<b>{user_pokemon}</b> победил!',
                        reply_markup=create_inline_kb(1, 'Продолжить', 'Вернуться в главное меню'))
                else:
                    await user_pokemon.drop_energy(callback.from_user.id, conn)
                    if data['my_point'] > data['enemy_point']:
                        await User(callback.from_user.id).add_icon(data["point"], conn)
                        await callback.message.edit_text(f'Ура! Вы выиграли <b>{data["icon"]}!</b>',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))
                    else:
                        await callback.message.edit_text('К сожалению вы проиграли!',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))

        # Ход противника (бота)
        else:
            dice_attack, dice_defence, damage, user_pokemon = get_fight(enemy_pokemon, user_pokemon)
            data['user_pokemon'] = user_pokemon
            await callback.answer(f'{enemy_pokemon} - {dice_attack} 🎲 (Атака)\n\n'
                                  f'{user_pokemon} - {dice_defence} 🎲 (Защита)', show_alert=True)
            if user_pokemon.hp > 0:
                await callback.message.edit_text(
                    get_text_for_fight(user_pokemon, enemy_pokemon, dice=data['dice'], damage=damage),
                    reply_markup=create_inline_kb(1, 'Атаковать!',
                                                  f'Усилить покемона ({data["eat"]} 🍔)',
                                                  'Сдаться 🏳️') if data['eat'] else
                    create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))
                data['dice'] += 1
            else:
                await user_pokemon.drop_energy(callback.from_user.id, conn)
                data['enemy_point'] += 1
                if data['my_point'] < 2 and data['enemy_point'] < 2:
                    data['level'] += 1
                    await callback.message.edit_text(f'<b>{enemy_pokemon}</b> победил!',
                                                     reply_markup=create_inline_kb(1, 'Продолжить',
                                                                                   'Вернуться в главное меню'))
                else:
                    if data['my_point'] > data['enemy_point']:
                        await User(callback.from_user.id).add_icon(data["point"], conn)
                        await callback.message.edit_text(f'Ура! Вы выиграли <b>{data["icon"]}!</b>',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))
                    else:
                        await callback.message.edit_text('К сожалению вы проиграли!',
                                                         reply_markup=create_inline_kb(1, 'Лига Покемонов 🏆',
                                                                                       'Вернуться в главное меню'))


def register_pokemon_league_handlers(dp: Dispatcher, names_pokemons):
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
