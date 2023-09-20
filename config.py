from dataclasses import dataclass

from environs import Env


@dataclass
class TokenConfig:
    token: str


@dataclass
class DBConfig:
    database: str
    user: str
    password: str
    host: str
    port: str


def load_token_config(path: str | None = None) -> TokenConfig:
    env = Env()
    env.read_env(path)
    return TokenConfig(token=env('Pokemon_token'))


def load_db_config(path: str | None = None) -> DBConfig:
    env = Env()
    env.read_env(path)
    return DBConfig(database=env('DATABASE'),
                    user=env('USER'),
                    password=env('PASSWORD'),
                    host=env('HOST'),
                    port=env('PORT')
                    )
