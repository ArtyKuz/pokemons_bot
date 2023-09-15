import random
import sqlite3

from services.classes import Pokemon


def get_pokemons_for_first_select():
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        data = [i[0] for i in cur.execute(f'SELECT Name FROM Pokemons WHERE Level = 1 AND Type <> "Психический 😵‍💫"'
                                       f'AND Type <> "Призрак 👻"').fetchall()]
        pokemons = random.sample(data, k=10)
        return set(pokemons)


def get_description(pokemon_name, full=True):
    '''Функция для получения описания покемона.
    Атрибут full используется для получения полного или сокращенного описания'''

    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        s = cur.execute(f'SELECT * FROM Pokemons WHERE Name = "{pokemon_name}"').fetchall()[0]
        if full:
            return s[8], f'<b>{s[9]}</b>\n\n<b>Характеристики:</b>\nЗдоровье 💊 - {s[3]}\nАтака ⚔ - {s[4]}\n' \
                         f'Защита 🛡 - {s[5]}\n\n<b>Имеет преимущества над типами:</b>\n{s[6]}'
        else:
            return s[8], f'<b>{pokemon_name}\n\n</b><b>Характеристики:</b>\nЗдоровье 💊 - {s[3]}\nАтака ⚔ - {s[4]}\n' \
                         f'Защита 🛡 - {s[5]}\n\n<b>Имеет преимущества над типами:</b>\n{s[6]}'


def get_best_pokemons(best: str) -> str:
    '''Функция возвращает строку с содержанием 10-ти лучших покемонов'''

    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        best_pokemons: str = f'{best}:\n\n'
        if best == 'Лучшие покемоны по сумме хар-к':
            s = cur.execute(
                f'SELECT Name, HP+Атака+Защита FROM Pokemons ORDER BY HP+Атака+Защита DESC LIMIT 10').fetchall()
            for ind, pokemon in enumerate(s, 1):
                best_pokemons += f'{ind}. {pokemon[0]} - {pokemon[1]}\n'

        elif best == 'Лучшие покемоны по Здоровью':
            s = cur.execute(
                f'SELECT Name, HP FROM Pokemons ORDER BY HP DESC LIMIT 10').fetchall()
            for ind, pokemon in enumerate(s, 1):
                best_pokemons += f'{ind}. {pokemon[0]} - {pokemon[1]}\n'

        elif best == 'Лучшие покемоны по Атаке':
            s = cur.execute(
                f'SELECT Name, Атака FROM Pokemons ORDER BY Атака DESC LIMIT 10').fetchall()
            for ind, pokemon in enumerate(s, 1):
                best_pokemons += f'{ind}. {pokemon[0]} - {pokemon[1]}\n'

        elif best == 'Лучшие покемоны по Защите':
            s = cur.execute(
                f'SELECT Name, Защита FROM Pokemons ORDER BY Защита DESC LIMIT 10').fetchall()
            for ind, pokemon in enumerate(s, 1):
                best_pokemons += f'{ind}. {pokemon[0]} - {pokemon[1]}\n'

        return best_pokemons


def access_to_hunting(id):
    '''Функция проверяет кол-во оставшихся попыток для игры в режиме Охоты на Покемонов'''

    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if cur.execute(f'SELECT hunting_attempts FROM Users WHERE id = {id}').fetchone()[0] > 0:
            return True
        return False


def get_pokemon_for_hunting():
    '''Функция выбирает рандомного покемона 0 или 1 уровня, для режима Охоты на Покемонов'''

    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        return random.choice([i[0] for i in cur.execute(f'SELECT name FROM Pokemons WHERE Level < 2').fetchall()])


def get_fight(pokemon1: Pokemon, pokemon2: Pokemon):
    '''Функция для расчета характеристик во время боя покемонов'''

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


# def take_pokemon(pokemon, id):
#     """Функция принимает Покемона и если у игрока меньше 10 покемонов
#     добавляет покемона игроку, иначе возвращает False"""
#
#     with sqlite3.connect('Pokemon.db') as base:
#         cur = base.cursor()
#         s: list = cur.execute(f'SELECT pokemons FROM Users WHERE id = {id}').fetchone()[0].split()
#         if len(s) < 10:
#             s.append(pokemon)
#             cur.execute("UPDATE Users SET pokemons = '{}' WHERE id = {}".format(' '.join(s), id))
#             base.commit()
#             return True
#         return False


def evolution_pokemon(pokemon, id):
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        level = cur.execute(f'SELECT Level FROM Pokemons WHERE Name = "{pokemon}"').fetchone()[0]
        if level == 0:
            return level
        p = [i[0] for i in cur.execute('SELECT Name FROM Pokemons GROUP BY Эволюция HAVING max(Level)').fetchall()]
        if pokemon in p:
            return 'max'
        stone = cur.execute(f'SELECT evolution_stone FROM Users WHERE id = {id}').fetchone()[0]
        if stone > 0:
            if pokemon == 'Иви':
                ev_pokemon = random.choice(cur.execute(f'SELECT Name FROM Pokemons WHERE Эволюция IN '
                                     f'(SELECT Эволюция FROM Pokemons WHERE Name = "{pokemon}") '
                                     f'AND Level = {level}+1').fetchall())[0]
            else:
                ev_pokemon = cur.execute(f'SELECT Name FROM Pokemons WHERE Эволюция IN '
                                     f'(SELECT Эволюция FROM Pokemons WHERE Name = "{pokemon}") '
                                     f'AND Level = {level}+1').fetchone()[0]
            user_pok: str = cur.execute(f'SELECT pokemons FROM Users WHERE id = {id}').fetchone()[0]
            user_pok = user_pok.replace(pokemon, ev_pokemon)
            cur.execute(f"UPDATE Users SET pokemons = '{user_pok}', evolution_stone = evolution_stone - 1"
                        f" WHERE id = {id}")
            base.commit()
            return ev_pokemon
        return False


def start_fortune(id):
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        attempts = cur.execute(f'SELECT wheel_of_Fortune FROM Users WHERE id = {id}').fetchone()[0]
        if attempts:
            wheel = ['eat', 10, 20, 50, 'evolution_stone']
            select = random.sample(wheel, counts=[10, 10, 5, 3, 2], k=1)[0]
            if select == 'eat':
                cur.execute(f"UPDATE Users SET eat = eat + 1, wheel_of_Fortune = 0 WHERE id = {id}")
            elif type(select) == int:
                cur.execute(f"UPDATE Users SET coins = coins + {select}, wheel_of_Fortune = 0 WHERE id = {id}")
            elif select == 'evolution_stone':
                cur.execute(f"UPDATE Users SET evolution_stone = evolution_stone + 1, wheel_of_Fortune = 0"
                            f" WHERE id = {id}")
            base.commit()
            return select
        return False


def buy_in_shop(product, id):
    prices = {'eat': 50, 'evolution_stone': 100}
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        coins = cur.execute(f'SELECT coins FROM Users WHERE id = {id}').fetchone()[0]
        if coins >= prices[product]:
            cur.execute(f"UPDATE Users SET {product} = {product}+1, coins = coins - {prices[product]} WHERE id = {id}")
            base.commit()
            return True
        return False


def update_icons(id, icon):
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        icons = cur.execute(f'SELECT icons FROM Users WHERE id = {id}').fetchone()[0]
        if icons:
            icons += f',{icon}'
            cur.execute(f'UPDATE Users SET icons = "{icons}", point = point+1 WHERE id = {id}')
            base.commit()
        else:
            cur.execute(f'UPDATE Users SET icons = "{icon}", point = point+1 WHERE id = {id}')
            base.commit()


def get_text_for_icons(point, text: str):
    new_text = text.split('\n')
    for i, line in enumerate(new_text[1:point], 1):
        new_text[i] = f'<s>{line}</s>'
    return '\n'.join(new_text)


def access_to_pokemon_league(user_id):
    with sqlite3.connect('Pokemon.db') as base:
        cur = base.cursor()
        if len(cur.execute(f'SELECT pokemons FROM Users WHERE id = {user_id}').fetchone()[0].split()) < 7:
            return False
        return True
