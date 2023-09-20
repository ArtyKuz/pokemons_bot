import asyncpg
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware


class DBMiddleware(BaseMiddleware):
    def __init__(self, pool: asyncpg.pool.Pool):
        super().__init__()
        self.pool = pool

    async def on_pre_process_message(self, message: types.Message, data: dict):
        # Получаем подключение из пула
        conn = await self.pool.acquire()
        # Сохраняем его в контексте сообщения
        data['conn'] = conn

    async def on_post_process_message(self, message: types.Message, result, data: dict):
        # Закрываем подключение
        await self.pool.release(data['conn'])
        # Удаляем его из контекста сообщения
        del data['conn']

    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        # Получаем подключение из пула
        conn = await self.pool.acquire()
        # Сохраняем его в контексте сообщения
        data['conn'] = conn

    async def on_post_process_callback_query(self, callback_query: types.CallbackQuery, result, data: dict):
        # Закрываем подключение
        await self.pool.release(data['conn'])
        # Удаляем его из контекста сообщения
        del data['conn']