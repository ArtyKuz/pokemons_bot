from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from user_handlers.pokedeks_handlers import register_pokedeks_handlers
from user_handlers.menu_handlers import register_menu_handlers
from user_handlers.game_handlers import register_game_handlers
from user_handlers.hunting_handlers import register_hunting_handlers
from user_handlers.pokemon_league_handlers import register_pokemon_league_handlers
from config import Config, load_config


config: Config = load_config()

storage: MemoryStorage = MemoryStorage()

# Создаем объекты бота и диспетчера
bot: Bot = Bot(token=config.token, parse_mode='HTML')
dp: Dispatcher = Dispatcher(bot, storage=storage)


async def set_main_menu(dp: Dispatcher):
    """Функция для создания списка с командами для кнопки menu"""

    main_menu_commands = [
        types.BotCommand(command='/start', description='Запустить бота'),
        types.BotCommand(command='/rules_game', description='Правила игры'),
        types.BotCommand(command='/help', description='Справка по работе бота')
    ]
    await dp.bot.set_my_commands(main_menu_commands)


register_menu_handlers(dp)
register_pokedeks_handlers(dp)
register_game_handlers(dp)
register_hunting_handlers(dp)
register_pokemon_league_handlers(dp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=set_main_menu)
