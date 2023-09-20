import random
import sqlite3
from datetime import date

import asyncpg
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery
from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from services.classes import Pokemon, User
from services.services import get_pokemon_for_hunting, get_fight, access_to_hunting, \
    get_text_for_fight, get_description, create_pokemon_for_fight
from lexicon.lexicon import LEXICON


async def start_hunting(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    current_date = callback.message.date.date()
    date_hunting = await conn.fetchval('SELECT date_hunting FROM users WHERE user_id = $1', callback.from_user.id)
    if date_hunting != current_date:
        await conn.execute('UPDATE users SET date_hunting = $1, hunting_attempts = 10 WHERE user_id = $2',
                           current_date, callback.from_user.id)
    await callback.message.edit_text(f'{LEXICON["start_hunting"]}',
                                     reply_markup=create_inline_kb(1, 'Начать охоту', 'Вернуться в главное меню'))


async def select_pokemons_for_hunting(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await FSMPokemon.hunting.set()
    await callback.answer()
    if await access_to_hunting(callback.from_user.id, conn):
        async with state.proxy() as data:
            data['pokemon'] = await get_pokemon_for_hunting(callback.from_user.id, conn)
            image, description = await get_description(data['pokemon'], conn, full=False)
            await callback.message.answer_photo(image, caption=description,
                                                reply_markup=create_inline_kb(1, 'Поймать покемона', 'Пропусить',
                                                                              'Вернуться в главное меню'))
    else:
        await callback.message.answer('Увы, на сегодня выши попытки исчерпаны, приходите завтра!',
                                      reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def hunting_pokemons(callback: CallbackQuery, conn: asyncpg.connection.Connection):
    await callback.answer()
    await conn.execute('UPDATE users SET hunting_attempts = hunting_attempts - 1  WHERE user_id = $1',
                       callback.from_user.id)
    pokemons = [i['pokemon_name'] for i in await conn.fetch(
        'SELECT pokemon_name FROM users_pokemons JOIN pokemons USING(pokemon_id) '
        'WHERE user_id = $1 AND energy > 0', callback.from_user.id)]
    if pokemons:
        await callback.message.answer('Выбери своего покемона чтобы начать сражение!',
                                      reply_markup=create_inline_kb(2, *pokemons))
    else:
        await callback.message.answer('К сожалению у всех ваших покемонов энергия на нуле, подождите пока они отдохнут',
                                      reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def start_fight(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        user_pokemon, enemy_pokemon = await create_pokemon_for_fight(callback.data, data['pokemon'], conn)
        data['user_pokemon'] = user_pokemon
        data['enemy_pokemon'] = enemy_pokemon
        data['eat'] = await conn.fetchval('SELECT eat FROM users WHERE user_id = $1', callback.from_user.id)
        data['dice'] = random.randrange(0, 2)
        if data['dice']:
            await callback.answer('🎲 Ваш ход будет первым!', show_alert=True)
        else:
            await callback.answer(f'🎲 {enemy_pokemon} будет атаковать первым!', show_alert=True)
        await callback.message.edit_text(
            f'💥💥💥\n\n<b>{user_pokemon}</b> против <b>{enemy_pokemon}</b>!\n\n💥💥💥',
            reply_markup=create_inline_kb(1, 'Начать бой!'))


async def fight(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        user_pokemon: Pokemon = data['user_pokemon']
        enemy_pokemon: Pokemon = data['enemy_pokemon']
        if 'Усилить покемона' in callback.data:
            data['eat'] -= 1
            data['user_pokemon'] = await user_pokemon.enhance(callback.from_user.id, conn)
            await callback.message.edit_text(get_text_for_fight(user_pokemon, enemy_pokemon, enhance=True),
                                             reply_markup=create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))

        elif callback.data == 'Сдаться 🏳️':
            await user_pokemon.drop_energy(callback.from_user.id, conn)
            await callback.message.edit_text('Бой окончен!', reply_markup=create_inline_kb(1, 'Продолжить охоту',
                                                                                           'Вернуться в главное меню'))
        else:
            # Ход игрока
            if data['dice']:
                dice_attack, dice_defence, damage, enemy_pokemon = get_fight(user_pokemon, enemy_pokemon)
                data['enemy_pokemon'] = enemy_pokemon
                await callback.answer(f'{user_pokemon.name} - {dice_attack} 🎲 (Атака)\n\n'
                                      f'{enemy_pokemon.name} - {dice_defence} 🎲 (Защита)', show_alert=True)
                if enemy_pokemon.hp > 0:
                    await callback.message.edit_text(get_text_for_fight(user_pokemon, enemy_pokemon, dice=data['dice'],
                                                                        damage=damage),
                                                     reply_markup=create_inline_kb(1, 'Ход противника', 'Сдаться 🏳️')
                                                     )
                    data['dice'] -= 1
                else:
                    await user_pokemon.drop_energy(callback.from_user.id, conn)
                    await callback.message.edit_text(
                        f'Ура! Вы победили! 🎊\n\nТеперь <b>{enemy_pokemon.name}</b> может стать вашим покемоном!',
                        reply_markup=create_inline_kb(1, 'Забрать покемона', 'Продолжить охоту',
                                                      'Вернуться в главное меню'
                                                      ))
            # Ход противника (бота)
            else:
                dice_attack, dice_defence, damage, user_pokemon = get_fight(enemy_pokemon, user_pokemon)
                data['user_pokemon'] = user_pokemon
                await callback.answer(f'{enemy_pokemon.name} - {dice_attack} 🎲 (Атака)\n\n'
                                      f'{user_pokemon.name} - {dice_defence} 🎲 (Защита)', show_alert=True)
                if user_pokemon.hp > 0:
                    await callback.message.edit_text(get_text_for_fight(user_pokemon, enemy_pokemon, dice=data['dice'],
                                                                        damage=damage),
                                                     reply_markup=create_inline_kb(1, 'Атаковать!',
                                                                                   f'Усилить покемона ({data["eat"]} 🍔)',
                                                                                   'Сдаться 🏳️') if data['eat'] else
                                                     create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))
                    data['dice'] += 1
                else:
                    await user_pokemon.drop_energy(callback.from_user.id, conn)
                    await callback.message.edit_text('Ваш покемон проиграл!',
                                                     reply_markup=create_inline_kb(1, 'Продолжить охоту',
                                                                                   'Вернуться в главное меню'))


async def handler_take_pokemon(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        user = User(callback.from_user.id)
        if await user.count_pokemons(conn) < 10:
            await user.add_pokemon(data['enemy_pokemon'].name, conn)
            await callback.message.edit_text(f'Поздравляю! Теперь {data["enemy_pokemon"].name} ваш покемон!',
                                             reply_markup=create_inline_kb(1, 'Продолжить охоту', 'Вернуться в '
                                                                                                  'главное меню'))
        else:
            await callback.message.edit_text('У вас уже есть 10 покемонов, желаете заменить кого нибудь?',
                                             reply_markup=create_inline_kb(1, 'Выбрать покемона для замены',
                                                                           'Продолжить охоту', 'Вернуться в '
                                                                                               'главное меню'))


async def select_replace_pokemon(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    await FSMPokemon.replace_pokemon.set()
    user_pokemons = await User(callback.from_user.id).get_pokemons(conn)
    await callback.message.edit_text('Выберите покемона которого хотите заменить.',
                                     reply_markup=create_inline_kb(2, *user_pokemons))


async def replace_pokemon(callback: CallbackQuery, state: FSMContext, conn: asyncpg.connection.Connection):
    async with state.proxy() as data:
        await User(callback.from_user.id).replace_pokemon(callback.data, data["enemy_pokemon"].name, conn)
        await callback.message.edit_text(f'Теперь {data["enemy_pokemon"].name} в списке ваших покемонов.',
                                         reply_markup=create_inline_kb(1, 'Продолжить охоту', 'Вернуться в главное '
                                                                                              'меню'))


def register_hunting_handlers(dp: Dispatcher, names_pokemons):
    dp.register_callback_query_handler(start_hunting, text='Охота на Покемонов 🎯', state=FSMPokemon.game)
    dp.register_callback_query_handler(select_pokemons_for_hunting, text=['Начать охоту', 'Пропусить',
                                                                          'Продолжить охоту'],
                                       state=(FSMPokemon.game, FSMPokemon.hunting, FSMPokemon.replace_pokemon))
    dp.register_callback_query_handler(hunting_pokemons, text='Поймать покемона', state=FSMPokemon.hunting)
    dp.register_callback_query_handler(start_fight, text=names_pokemons, state=FSMPokemon.hunting)
    dp.register_callback_query_handler(fight, text=['Начать бой!', 'Атаковать!', 'Ход противника', 'Сдаться 🏳️'],
                                       state=FSMPokemon.hunting)
    dp.register_callback_query_handler(fight, Text(startswith='Усилить покемона'), state=FSMPokemon.hunting)
    dp.register_callback_query_handler(handler_take_pokemon, text='Забрать покемона', state=FSMPokemon.hunting)
    dp.register_callback_query_handler(select_replace_pokemon, text='Выбрать покемона для замены',
                                       state=FSMPokemon.hunting)
    dp.register_callback_query_handler(replace_pokemon, text=names_pokemons, state=FSMPokemon.replace_pokemon)
