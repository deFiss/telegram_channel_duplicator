from telethon import TelegramClient, events, sync
from .chat_controller import ChatController
import os
from loguru import logger


class Client:

    def __init__(self):
        api_id = int(os.getenv('ACCOUNT_API_ID'))
        api_hash = os.getenv('ACCOUNT_API_HASH')

        self.client = sync.TelegramClient('account_session', api_id, api_hash)
        logger.info('Авторизация в аккаунт')
        self.client.start(
            phone=self._get_phone,
            code_callback=self._enter_code,
            password=self._enter_password,
        )
        logger.info(f'Авторизация в аккаунт {self.client.get_me().first_name} прошла успешно')

        self.chat_controller = ChatController(self.client)

        self.client.add_event_handler(self.new_channel_post_handler, events.NewMessage(incoming=True))

        logger.info('Прослушивание каналов запущено...')
        self.client.run_until_disconnected()

    @staticmethod
    def _get_phone():
        return os.getenv('ACCOUNT_PHONE')

    @staticmethod
    def _enter_code():
        return input('Введите код из сообщения Telegram: ')

    @staticmethod
    def _enter_password():
        return input('Введите пароль двухфакторной аутентификации: ')

    async def get_dialog(self, dialog_name):
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            if dialog.name == dialog_name:
                return dialog

        return 0

    async def new_channel_post_handler(self, event):

        output_chats = self.chat_controller.filter_chat(event.chat_id)

        if output_chats:
            logger.info(f'Новое сообщение в канале, event: {event}')

        for chat in output_chats:
            logger.info(f'Отправка в чат {chat}')
            await self.client.send_message(chat, event.message)
