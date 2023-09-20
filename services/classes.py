import sqlite3
import random
from io import BytesIO

import asyncpg
from aiogram.types import InputFile


class Pokemon:
    def __init__(self, description, types):
        self.id: int = description['pokemon_id']
        self.name: str = description['pokemon_name']
        self.type: str = description['name_type']
        self.hp: int = description['hp']
        self.attack: int = description['attack']
        self.defense: int = description['defense']
        self.superiority: list[str] = [i['name_type'] for i in types]

    def __str__(self):
        return self.name

    # def get_description(self, full=True):
    #     """Функция для получения описания покемона.
    #     Атрибут full используется для получения полного или сокращенного описания."""
    #
    #     # s = cur.execute(f'SELECT * FROM Pokemons WHERE Name = "{pokemon_name}"').fetchall()[0]
    #     if full:
    #         return self.image, f'<b>{self.description}</b>\n\n<b>Характеристики:</b>\n' \
    #                            f'Здоровье 💊 - {self.hp}\nАтака ⚔ - {self.attack}\n' \
    #                            f'Защита 🛡 - {self.defense}\n\n<b>Имеет преимущества над типами:</b>\n' \
    #                            f'{", ".join(self.superiority)}'
    #     else:
    #         return self.image, f'<b>{self.name}\n\n</b><b>Характеристики:</b>\n' \
    #                            f'Здоровье 💊 - {self.hp}\nАтака ⚔ - {self.attack}\n' \
    #                            f'Защита 🛡 - {self.defense}\n\n<b>Имеет преимущества над типами:</b>\n' \
    #                            f'{", ".join(self.superiority)}'

    async def enhance(self, user_id, conn: asyncpg.connection.Connection):
        """Функция для повышения характеристик покемона после
        применения 'еды для усиления покемона'"""

        self.hp += 10
        self.attack += 10
        self.defense += 10
        await conn.execute(f"UPDATE users SET eat = eat - 1 WHERE user_id = {user_id}")

        return self

    async def drop_energy(self, user_id, conn: asyncpg.connection.Connection):
        """Уменьшает энергию покемона"""

        await conn.execute('UPDATE users_pokemons SET energy = energy - 1 '
                           'WHERE user_id = $1 AND pokemon_id = $2', user_id, self.id)


class User:
    def __init__(self, user_id):
        self.user_id = user_id

    async def check_user(self, conn: asyncpg.connection.Connection) -> bool:
        """Проверяет, есть ли пользователь в базе данных"""

        user = await conn.fetch(f'SELECT * FROM users WHERE user_id = {self.user_id}')
        return True if user else False

    async def add_user_in_db(self, username: str, conn: asyncpg.connection.Connection) -> None:
        """Добавляет пользователя в базу данных"""

        await conn.execute(f"INSERT INTO users (user_id, username) VALUES ({self.user_id}, '{username}')")

    async def add_pokemon(self, pokemon: str, conn: asyncpg.connection.Connection) -> None:
        """Добавляет покемона пользователю"""

        await conn.execute("INSERT INTO users_pokemons (user_id, pokemon_id) "
                           "VALUES($1, (SELECT pokemon_id FROM pokemons WHERE pokemon_name = $2))",
                           self.user_id, pokemon)

    async def count_pokemons(self, conn: asyncpg.connection.Connection) -> int:
        """Возвращает кол-во покемонов, которые есть у пользователя"""

        pokemons = await self.get_pokemons(conn)
        return len(pokemons) if pokemons else 0

    async def get_pokemons(self, conn: asyncpg.connection.Connection) -> list | None:
        """Возвращает список всех покемонов пользователя"""

        pokemons = await conn.fetch(f'SELECT pokemon_name FROM users_pokemons '
                                    f'JOIN pokemons USING(pokemon_id) WHERE user_id = {self.user_id}')
        if pokemons:
            return [i['pokemon_name'] for i in pokemons]

    async def get_backpack(self, conn: asyncpg.connection.Connection):
        """Возвращает содержимое рюкзака"""

        result = await conn.fetchrow('SELECT coins, eat, evolution_stone FROM users WHERE user_id = $1', self.user_id)
        icons = '-'
        user_icons = await conn.fetch('SELECT name_icon FROM icons JOIN users_icons USING(icon_id) '
                                      'WHERE user_id = $1', self.user_id)
        if user_icons:
            icons = [f'- {icon["name_icon"]}' for icon in user_icons]
            icons = '\n'.join(icons)
        return result['coins'], result['eat'], result['evolution_stone'], icons

    async def replace_pokemon(self, user_pokemon: str, new_pokemon: str, conn: asyncpg.connection.Connection) -> None:
        """Заменяет одного покемона на другого в списке покемонов пользователя"""

        user_pokemon_id = await conn.fetchval('SELECT pokemon_id FROM pokemons WHERE pokemon_name = $1', user_pokemon)
        new_pokemon_id = await conn.fetchval('SELECT pokemon_id FROM pokemons WHERE pokemon_name = $1', new_pokemon)
        await conn.execute('UPDATE users_pokemons SET pokemon_id = $1 WHERE user_id = $2 AND pokemon_id = $3',
                           new_pokemon_id, self.user_id, user_pokemon_id)
