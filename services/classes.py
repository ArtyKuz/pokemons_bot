import sqlite3
import random


class Pokemon:
    def __init__(self, name):
        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            s = [i for i in cur.execute(f'SELECT Type, HP, Атака, Защита, Преимущество FROM Pokemons WHERE Name = '
                                        f'"{name}"').fetchall()[0]]
            self.name: str = name
            self.type: str = s[0]
            self.hp: int = s[1]
            self.attack: int = s[2]
            self.defense: int = s[3]
            self.superiority: list[str] = [i.strip() for i in s[4].split(',')]

    def __str__(self):
        return self.name

    def enhance(self, user_id):
        """Функция для повышения характеристик покемона после
        применения 'еды для усиления покемона'"""

        self.hp += 10
        self.attack += 10
        self.defense += 10
        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            cur.execute(f"UPDATE Users SET eat = eat - 1 WHERE id = {user_id}")
            base.commit()
        return self


class User:
    def __init__(self, user_id):
        self.user_id = user_id

    def check_user(self) -> bool:
        """Проверяет, есть ли пользователь в базе данных"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            if cur.execute(f'SELECT * FROM Users WHERE id = {self.user_id}').fetchone() is None:
                return False
            return True

    def add_user_in_db(self, first_name: str, last_name: str) -> None:
        """Добавляет пользователя в базу данных"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            cur.execute(f"INSERT INTO Users (id, user_name) VALUES ({self.user_id}, '{first_name} {last_name}')")
            base.commit()

    def add_pokemon(self, pokemon: str) -> None:
        """Добавляет покемона пользователю"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            pokemons = self.get_pokemons()
            if pokemons is None:
                cur.execute(f"UPDATE Users SET pokemons = '{pokemon}' WHERE id = {self.user_id}")
                base.commit()
            else:
                pokemons += f' {pokemon}'
                cur.execute(f"UPDATE Users SET pokemons = '{pokemons}' WHERE id = {self.user_id}")
                base.commit()

    def count_pokemons(self) -> int:
        """Возвращает кол-во покемонов, которые есть у пользователя"""

        pokemons = self.get_pokemons()
        return len(pokemons) if pokemons else 0

    def get_pokemons(self) -> list:
        """Возвращает список всех покемонов пользователя"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            pokemons = cur.execute(f'SELECT pokemons FROM Users WHERE id = {self.user_id}').fetchone()[0]
            if pokemons:
                return pokemons.split()

    def get_backpack(self):
        """Возвращает содержимое рюкзака"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            coins, eat, stone, icons = cur.execute(f'SELECT coins, eat, evolution_stone, icons FROM Users WHERE id = '
                                                   f'{self.user_id}').fetchall()[0]
            icons = [f'- {icon}' for icon in icons.split(',')]
            icons = '\n'.join(icons)
            return coins, eat, stone, icons

    def replace_pokemon(self, user_pokemon: str, new_pokemon: str) -> None:
        """Заменяет одного покемона на другого в списке покемонов пользователя"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            pokemons = self.get_pokemons()
            index = pokemons.index(user_pokemon)
            pokemons[index] = new_pokemon
            cur.execute(f"UPDATE Users SET pokemons = '{' '.join(pokemons)}' WHERE id = {self.user_id}")
            base.commit()
