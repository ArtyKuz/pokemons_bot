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

    def check_user(self):
        """Проверяет, есть ли пользователь в базе данных"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            if cur.execute(f'SELECT * FROM Users WHERE id = {self.user_id}').fetchone() is None:
                return False
            return True

    def add_user_in_db(self, first_name, last_name):
        """Добавляет пользователя в базу данных"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            cur.execute(f"INSERT INTO Users (id, user_name) VALUES ({self.user_id}, '{first_name} {last_name}')")
            base.commit()

    def check_count_pokemons(self):
        """Проверяет количество покемонов у пользователя"""

        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            pokemons = cur.execute(f'SELECT pokemons FROM Users WHERE id = {self.user_id}').fetchone()[0]
            if pokemons is None:
                return False
            elif len(pokemons.split()) < 3:
                return False

            return True
