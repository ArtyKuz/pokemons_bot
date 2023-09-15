import random
import sqlite3
from datetime import date
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery
from FSM import FSMPokemon
from keyboard.keyboards import create_inline_kb
from services.classes import Pokemon, User
from services.services import get_description, get_pokemon_for_hunting, get_fight, access_to_hunting, \
    get_text_for_fight
from lexicon.lexicon import LEXICON

base = sqlite3.connect('Pokemon.db')
cur = base.cursor()
names_pokemons = [i[0] for i in cur.execute('SELECT Name FROM Pokemons').fetchall()]
base.close()


async def start_hunting(callback: CallbackQuery, state: FSMContext):
    user_date = callback.message.date.date().strftime('%d.%m.%Y')
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if cur.execute(f'SELECT date_hunting FROM Users WHERE id = {callback.from_user.id}').fetchone()[0] != user_date:
            cur.execute(
                f'UPDATE Users SET date_hunting = "{user_date}", hunting_attempts = 10 WHERE id = {callback.from_user.id}')
            base.commit()

    await callback.message.edit_text(f'{LEXICON["start_hunting"]}',
                                     reply_markup=create_inline_kb(1, 'Начать охоту', 'Вернуться в главное меню'))


async def select_pokemons_for_hunting(callback: CallbackQuery, state: FSMContext):
    await FSMPokemon.hunting.set()
    await callback.answer()
    if access_to_hunting(callback.from_user.id):
        async with state.proxy() as data:
            data['pokemon'] = get_pokemon_for_hunting()
            image, description = get_description(data['pokemon'], full=False)
            await callback.message.answer_photo(image, caption=description,
                                                reply_markup=create_inline_kb(1, 'Поймать покемона', 'Пропусить',
                                                                              'Вернуться в главное меню'))
    else:
        await callback.message.answer('Увы, на сегодня выши попытки исчерпаны, приходите завтра!',
                                      reply_markup=create_inline_kb(1, 'Вернуться в главное меню'))


async def hunting_pokemons(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        cur.execute(f'UPDATE Users SET hunting_attempts = hunting_attempts - 1  WHERE id = {callback.from_user.id}')
        base.commit()
        s = cur.execute(f'SELECT pokemons FROM Users WHERE id = {callback.from_user.id}').fetchone()[0].split()

        await callback.message.answer('Выбери своего покемона чтобы начать сражение!',
                                      reply_markup=create_inline_kb(2, *s))


async def start_fight(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        user_pokemon = Pokemon(callback.data)
        enemy_pokemon = Pokemon(data['pokemon'])
        data['user_pokemon'] = user_pokemon
        data['enemy_pokemon'] = enemy_pokemon
        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            data['eat'] = cur.execute(f'SELECT eat FROM Users WHERE id = {callback.from_user.id}').fetchone()[0]
        data['dice'] = random.randrange(0, 2)
        if data['dice']:
            await callback.answer('🎲 Ваш ход будет первым!', show_alert=True)
        else:
            await callback.answer(f'🎲 {enemy_pokemon} будет атаковать первым!', show_alert=True)
        await callback.message.edit_text(
            f'💥💥💥\n\n<b>{user_pokemon}</b> против <b>{enemy_pokemon}</b>!\n\n💥💥💥',
            reply_markup=create_inline_kb(1, 'Начать бой!'))


async def fight(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        user_pokemon: Pokemon = data['user_pokemon']
        enemy_pokemon: Pokemon = data['enemy_pokemon']
        if 'Усилить покемона' in callback.data:
            data['eat'] -= 1
            data['user_pokemon'] = user_pokemon.enhance(callback.from_user.id)
            await callback.message.edit_text(get_text_for_fight(user_pokemon, enemy_pokemon, enhance=True),
                                             reply_markup=create_inline_kb(1, 'Атаковать!', 'Сдаться 🏳️'))

        elif callback.data == 'Сдаться 🏳️':
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
                    await callback.message.edit_text('Ваш покемон проиграл!',
                                                     reply_markup=create_inline_kb(1, 'Продолжить охоту',
                                                                                   'Вернуться в главное меню'))


async def handler_take_pokemon(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        user = User(callback.from_user.id)
        if user.count_pokemons() < 10:
            user.add_pokemon(data['enemy_pokemon'].name)
            await callback.message.edit_text(f'Поздравляю! Теперь {data["enemy_pokemon"].name} ваш покемон!',
                                             reply_markup=create_inline_kb(1, 'Продолжить охоту', 'Вернуться в '
                                                                                                  'главное меню'))
        else:
            await callback.message.edit_text('У вас уже есть 10 покемонов, желаете заменить кого нибудь?',
                                             reply_markup=create_inline_kb(1, 'Выбрать покемона для замены',
                                                                           'Продолжить охоту', 'Вернуться в '
                                                                                               'главное меню'))


async def select_replace_pokemon(callback: CallbackQuery, state: FSMContext):
    await FSMPokemon.replace_pokemon.set()
    user_pokemons = User(callback.from_user.id).get_pokemons()
    await callback.message.edit_text('Выберите покемона которого хотите заменить.',
                                     reply_markup=create_inline_kb(2, *user_pokemons))


async def replace_pokemon(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        User(callback.from_user.id).replace_pokemon(callback.data, data["enemy_pokemon"].name)
        await callback.message.edit_text(f'Теперь {data["enemy_pokemon"].name} в списке ваших покемонов.',
                                         reply_markup=create_inline_kb(1, 'Продолжить охоту', 'Вернуться в главное '
                                                                                              'меню'))


def register_hunting_handlers(dp: Dispatcher):
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
