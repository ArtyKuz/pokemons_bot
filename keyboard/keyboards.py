from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)


def create_kb(row_width: int, *args) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
    [keyboard.insert(button) for button in args]
    return keyboard


def create_inline_kb(row_width: int, *args, **kwargs) -> InlineKeyboardMarkup:
    inline_kb: InlineKeyboardMarkup = InlineKeyboardMarkup(row_width=row_width)
    if args:
        [inline_kb.insert(InlineKeyboardButton(
                            text=button,
                            callback_data=button)) for button in args]
        return inline_kb
    if kwargs:
        [inline_kb.insert(InlineKeyboardButton(
            text=button,
            callback_data=kwargs[button])) for button in kwargs]
        return inline_kb