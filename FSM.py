from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup


class FSMPokemon(StatesGroup):
    pokedeks = State()
    game = State()
    first_select = State()
    hunting = State()
    replace_pokemon = State()
    pokemon_league = State()
  #  fight_pokemons = State()