import asyncio
import random
from io import BytesIO
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
from aiogram.types import InputFile

from services.classes import Pokemon


async def get_pokemons_for_first_select(conn: asyncpg.connection.Connection) -> set:
    """Выбирает 10 случайных покемонов 1 уровня для выбора в начале игры."""

    pokemons = await conn.fetch(f'SELECT pokemon_name FROM pokemons '
                                f'WHERE level = 1 AND type_pokemon != 8 AND type_pokemon != 9')
    data = [i['pokemon_name'] for i in pokemons]
    pokemons = random.sample(data, k=10)
    return set(pokemons)


async def get_description(pokemon_name, conn: asyncpg.connection.Connection, full=True, user_id=None):
    """Функция для получения описания покемона.
    Атрибут full используется для получения полного или сокращенного описания."""

    pokemon = await conn.fetchrow(
        "SELECT pokemon_id, pokemon_name, name_type, type_pokemon, hp, attack, defense, image, description "
        'FROM pokemons JOIN types_pokemons ON pokemons.type_pokemon = types_pokemons.type_id '
        'WHERE pokemon_name = $1', pokemon_name)
    types = await conn.fetch("SELECT name_type FROM types_pokemons "
                             "WHERE type_id IN "
                             "(SELECT superiority_type FROM superiority "
                             "WHERE type_id = $1)", pokemon['type_pokemon'])
    superiority = ', '.join([i['name_type'] for i in types])
    image = InputFile(BytesIO(pokemon['image']))
    if full:
        return image, f'<b>{pokemon["description"]}</b>\n\n<b>Характеристики:</b>\nЗдоровье 💊 - {pokemon["hp"]}\n' \
                      f'Атака ⚔ - {pokemon["attack"]}\nЗащита 🛡 - {pokemon["defense"]}\n\n' \
                      f'<b>Имеет преимущества над типами:</b>\n{superiority}'
    elif not full and not user_id:
        return image, f'<b>{pokemon_name}</b>\nТип - {pokemon["name_type"]}\n\n<b>Характеристики:</b>\n' \
                      f'Здоровье 💊 - {pokemon["hp"]}\n' \
                      f'Атака ⚔ - {pokemon["attack"]}\n' \
                      f'Защита 🛡 - {pokemon["defense"]}\n\n' \
                      f'<b>Имеет преимущества над типами:</b>\n{superiority}'
    else:
        energy = await conn.fetchval('SELECT energy FROM users_pokemons WHERE user_id = $1 AND pokemon_id = $2',
                                     user_id, pokemon["pokemon_id"])
        return image, f'<b>{pokemon_name}</b>\nТип - {pokemon["name_type"]}\n\n<b>Характеристики:</b>\n' \
                      f'Здоровье 💊 - {pokemon["hp"]}\n' \
                      f'Атака ⚔ - {pokemon["attack"]}\n' \
                      f'Защита 🛡 - {pokemon["defense"]}\n\n' \
                      f'Энергия ⚡ - {energy}\n\n' \
                      f'<b>Имеет преимущества над типами:</b>\n{superiority}'


async def create_pokemon_for_fight(pokemon, conn: asyncpg.connection.Connection):
    description, superiority = await get_data(pokemon, conn)
    return Pokemon(description, superiority)


async def get_data(name_pokemon, conn: asyncpg.connection.Connection):
    description = await conn.fetchrow(
        "SELECT pokemon_id, pokemon_name, name_type, type_pokemon, hp, attack, defense "
        'FROM pokemons JOIN types_pokemons ON pokemons.type_pokemon = '
        'types_pokemons.type_id '
        'WHERE pokemon_name = $1', name_pokemon)
    superiority = await conn.fetch("SELECT name_type FROM types_pokemons "
                                   "WHERE type_id IN "
                                   "(SELECT superiority_type FROM superiority "
                                   "WHERE type_id = $1)", description['type_pokemon'])
    return description, superiority


async def get_best_pokemons(best: str, conn: asyncpg.connection.Connection) -> str:
    '''Функция возвращает строку с содержанием 10-ти лучших покемонов'''

    best_pokemons: str = f'{best}:\n\n'
    if best == 'Лучшие покемоны по сумме хар-к':
        s = await conn.fetch(
            f'SELECT pokemon_name, (hp+attack+defense) as power FROM pokemons ORDER BY power DESC LIMIT 10')
        for ind, pokemon in enumerate(s, 1):
            best_pokemons += f'{ind}. {pokemon["pokemon_name"]} - {pokemon["power"]}\n'

    elif best == 'Лучшие покемоны по Здоровью':
        s = await conn.fetch(
            f'SELECT pokemon_name, hp FROM Pokemons ORDER BY hp DESC LIMIT 10')
        for ind, pokemon in enumerate(s, 1):
            best_pokemons += f'{ind}. {pokemon["pokemon_name"]} - {pokemon["hp"]}\n'

    elif best == 'Лучшие покемоны по Атаке':
        s = await conn.fetch(
            f'SELECT pokemon_name, attack FROM pokemons ORDER BY attack DESC LIMIT 10')
        for ind, pokemon in enumerate(s, 1):
            best_pokemons += f'{ind}. {pokemon["pokemon_name"]} - {pokemon["attack"]}\n'

    elif best == 'Лучшие покемоны по Защите':
        s = await conn.fetch(
            f'SELECT pokemon_name, defense FROM pokemons ORDER BY defense DESC LIMIT 10')
        for ind, pokemon in enumerate(s, 1):
            best_pokemons += f'{ind}. {pokemon["pokemon_name"]} - {pokemon["defense"]}\n'

    return best_pokemons


async def access_to_hunting(user_id, conn: asyncpg.connection.Connection):
    """Функция проверяет кол-во оставшихся попыток для игры в режиме Охоты на Покемонов"""

    if await conn.fetchval(f'SELECT hunting_attempts FROM users WHERE user_id = $1', user_id):
        return True
    return False


async def get_pokemon_for_hunting(user_id, conn: asyncpg.connection.Connection):
    """Функция выбирает рандомного покемона 0 или 1 уровня, для режима Охоты на Покемонов"""

    return random.choice([i['pokemon_name'] for i in await conn.fetch(f'SELECT pokemon_name FROM pokemons '
                                                                      f'WHERE level < 2 AND pokemon_id NOT IN '
                                                                      f'(SELECT pokemon_id FROM users_pokemons '
                                                                      f'WHERE user_id = $1)', user_id)])


def get_fight(pokemon1: Pokemon, pokemon2: Pokemon):
    """Функция для расчета характеристик во время боя покемонов"""

    dice_attack = random.randrange(1, 7)
    dice_defense = random.randrange(1, 7)
    if (pokemon2.type in pokemon1.superiority) and dice_attack < 6:
        dice_attack += 1
    if (pokemon1.type in pokemon2.superiority) and dice_defense < 6:
        dice_defense += 1
    attack = pokemon1.attack * (dice_attack / 10)
    defense = pokemon2.defense * (dice_defense / 10)
    damage = round(attack - defense) if round(attack - defense) > 0 else 0
    pokemon2.hp -= damage
    return dice_attack, dice_defense, damage, pokemon2


def get_text_for_fight(user_pokemon: Pokemon, enemy_pokemon: Pokemon, dice=None, damage=None, enhance=None):
    if enhance:
        return f'<b>{user_pokemon.name}</b>\n' \
               f'Здоровье 💊 - <b>{user_pokemon.hp} (+10)</b>\n' \
               f'Атака ⚔ - <b>{user_pokemon.attack} (+10)</b>\n' \
               f'Защита 🛡 - <b>{user_pokemon.defense} (+10)</b>\n' \
               f'----------------------------------------------------------\n' \
               f'<b>{enemy_pokemon.name}</b>\n' \
               f'Здоровье 💊 - <b>{enemy_pokemon.hp}</b>\n' \
               f'Атака ⚔ - <b>{enemy_pokemon.attack}</b>\n' \
               f'Защита 🛡 - <b>{enemy_pokemon.defense}</b>'
    elif dice:
        text = f'{user_pokemon.name} наносит <b>{damage}</b> урона! 💥\n\n'
    else:
        text = f'{enemy_pokemon.name} наносит <b>{damage}</b> урона! 💥\n\n'
    text += f'<b>{user_pokemon.name}</b>\n' \
            f'Здоровье 💊 - <b>{user_pokemon.hp}</b>\n' \
            f'Атака ⚔ - <b>{user_pokemon.attack}</b>\n' \
            f'Защита 🛡 - <b>{user_pokemon.defense}</b>\n' \
            f'----------------------------------------------------------\n' \
            f'<b>{enemy_pokemon.name}</b>\n' \
            f'Здоровье 💊 - <b>{enemy_pokemon.hp}</b>\n' \
            f'Атака ⚔ - <b>{enemy_pokemon.attack}</b>\n' \
            f'Защита 🛡 - <b>{enemy_pokemon.defense}</b>'
    return text


async def evolution_pokemon(pokemon, user_id, conn: asyncpg.connection.Connection):
    level = await conn.fetchval(f'SELECT level FROM pokemons WHERE pokemon_name = $1', pokemon)
    if level == 0:
        return level
    max_level = await conn.fetch('SELECT max(level) FROM pokemons WHERE evolution_group IN (SELECT evolution_group '
                                 'FROM pokemons WHERE pokemon_name = $1)', pokemon)
    if level == max_level:
        return 'max'
    stone = await conn.fetchval(f'SELECT evolution_stone FROM users WHERE user_id = $1', user_id)
    if stone > 0:
        level += 1
        if pokemon == 'Иви':
            new_pokemon = random.choice(
                [i['pokemon_name'] for i in await conn.fetch(f'SELECT pokemon_name FROM pokemons '
                                                             f'WHERE evolution_group IN '
                                                             f'(SELECT evolution_group FROM pokemons '
                                                             f'WHERE pokemon_name = $1) '
                                                             f'AND level = $2', pokemon, level)])
        else:
            new_pokemon = await conn.fetchval(f'SELECT pokemon_name FROM pokemons '
                                              f'WHERE evolution_group IN '
                                              f'(SELECT evolution_group FROM pokemons '
                                              f'WHERE pokemon_name = $1) '
                                              f'AND level = $2', pokemon, level)
        new_pokemon_id = await conn.fetchval('SELECT pokemon_id FROM pokemons WHERE pokemon_name = $1', new_pokemon)
        old_pokemon_id = await conn.fetchval('SELECT pokemon_id FROM pokemons WHERE pokemon_name = $1', pokemon)

        await conn.execute('UPDATE users_pokemons SET pokemon_id = $1, energy = $2, wins = $3 '
                           'WHERE user_id = $4 AND pokemon_id = $5', new_pokemon_id, 3, 0, user_id, old_pokemon_id)

        await conn.execute("UPDATE users SET evolution_stone = evolution_stone - 1 "
                           f"WHERE user_id = $1", user_id)
        return new_pokemon
    return False


async def start_fortune(user_id, conn: asyncpg.connection.Connection):
    attempts = await conn.fetchval('SELECT fortune_attempts FROM users WHERE user_id = $1', user_id)
    if attempts:
        wheel = ['eat', 10, 20, 50, 'evolution_stone']
        select = random.sample(wheel, counts=[10, 10, 5, 3, 2], k=1)[0]
        if select == 'eat':
            await conn.execute("UPDATE users SET eat = eat + 1, fortune_attempts = 0 WHERE user_id = $1", user_id)
            return select
        elif type(select) == int:
            await conn.execute("UPDATE users SET coins = coins + $1, fortune_attempts = 0 WHERE user_id = $2",
                               select, user_id)
            return select
        elif select == 'evolution_stone':
            await conn.execute("UPDATE users SET evolution_stone = evolution_stone + $1, fortune_attempts = 0"
                               f" WHERE user_id = $2", select, user_id)
            return select
    return False


async def buy_in_shop(product, user_id, conn: asyncpg.connection.Connection):
    menu = {'eat': 50, 'evolution_stone': 100}

    coins = await conn.fetchval('SELECT coins FROM users WHERE user_id = $1', user_id)
    if coins >= menu[product]:
        query = f'UPDATE users SET {product} = {product} + 1, coins = coins - $1 WHERE user_id = $2'
        await conn.execute(query, menu[product], user_id)
        return True
    return False


def get_text_for_icons(point, text: str):
    new_text = text.split('\n')
    for i, line in enumerate(new_text[1:point], 1):
        new_text[i] = f'<s>{line}</s>'
    return '\n'.join(new_text)


async def get_pokemons_icon(point, conn: asyncpg.connection.Connection):
    return [i['pokemon_name'] for i in await conn.fetch('SELECT pokemon_name FROM pokemons '
                                                        'JOIN icon_pokemons USING(pokemon_id) '
                                                        'WHERE icon_id = $1', point)]


async def recovery_energy(pool):
    print('recovery_energy')
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users_pokemons SET energy = energy + 1 WHERE energy < 3')


async def recovery_attempts(pool):
    print('recovery_attempts')
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET hunting_attempts = 10, fortune_attempts = 1')


async def func_scheduler(pool):
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    start_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    scheduler.add_job(recovery_energy, trigger='interval', hours=1, start_date=start_date, args=[pool])
    scheduler.add_job(recovery_attempts, 'cron', hour=0, minute=0, args=[pool])
    scheduler.start()
    while True:
        await asyncio.sleep(1)
