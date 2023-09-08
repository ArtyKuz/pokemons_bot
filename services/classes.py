import sqlite3
import random


class Pokemon:
    def __init__(self, name):
        self.name = name
        self.type = None
        self.hp = None
        self.attack = None
        self.defense = None
        self.superiority = None
        self.get_characteristic(name)

    def __str__(self):
        return self.name

    def get_characteristic(self, name):
        with sqlite3.connect('Pokemon.db') as base:
            cur = base.cursor()
            s = [i for i in cur.execute(f'SELECT Type, HP, Атака, Защита, Преимущество FROM Pokemons WHERE Name = '
                                        f'"{name}"').fetchall()[0]]
            self.type = s[0]
            self.hp = s[1]
            self.attack = s[2]
            self.defense = s[3]
            self.superiority = [i.strip() for i in s[4].split(',')]

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





