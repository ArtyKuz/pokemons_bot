import asyncio

import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import DBConfig, TokenConfig, load_db_config, load_token_config
from middlewares.middlewares import DBMiddleware
from services.services import func_scheduler
from user_handlers.game_handlers import register_game_handlers
from user_handlers.hunting_handlers import register_hunting_handlers
from user_handlers.menu_handlers import register_menu_handlers
from user_handlers.pokedeks_handlers import register_pokedeks_handlers
from user_handlers.pokemon_league_handlers import \
    register_pokemon_league_handlers

token_config: TokenConfig = load_token_config()
db_config: DBConfig = load_db_config()

storage: MemoryStorage = MemoryStorage()
# storage: RedisStorage2 = RedisStorage2(db=6)

# Создаем объекты бота и диспетчера
bot: Bot = Bot(token=token_config.token, parse_mode='HTML')
dp: Dispatcher = Dispatcher(bot, storage=storage)


async def main():

    main_menu_commands = [
        types.BotCommand(command='/start', description='Запустить бота'),
        types.BotCommand(command='/rules_game', description='Правила игры'),
        types.BotCommand(command='/help', description='Справка по работе бота')
    ]
    await dp.bot.set_my_commands(main_menu_commands)

    pool = await asyncpg.create_pool(database=db_config.database,
                                     user=db_config.user,
                                     password=db_config.password,
                                     host=db_config.host,
                                     port=db_config.port)
    db_middleware = DBMiddleware(pool)

    # Добавляем мидлвари в диспетчер
    dp.middleware.setup(db_middleware)
    asyncio.create_task(func_scheduler(pool))

    async with pool.acquire() as conn:
        types_pok = [i['name_type'] for i in await conn.fetch('SELECT name_type FROM types_pokemons')]
        names_pokemons = [i['pokemon_name'] for i in await conn.fetch('SELECT pokemon_name FROM pokemons')]
    register_menu_handlers(dp)
    register_pokedeks_handlers(dp, types_pok, names_pokemons)
    register_game_handlers(dp, names_pokemons)
    register_hunting_handlers(dp, names_pokemons)
    register_pokemon_league_handlers(dp, names_pokemons)
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
