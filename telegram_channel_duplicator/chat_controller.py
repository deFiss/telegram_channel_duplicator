import os
from loguru import logger
import sys


class ChatController:
    def __init__(self, client):
        self._client = client
        self.groups = []

        self._parse_env()

    def filter_chat(self, chat_id):
        for group in self.groups:
            if chat_id in group['input_chats']:
                return group['output_chats']

        return []

    def _parse_env(self):
        logger.debug('Чтение групп')
        for index in range(1, 100):
            raw_str = os.getenv('GROUP_'+str(index))

            if not raw_str:
                break

            logger.debug(f'Найдена группа с индексом {index}')

            raw_str = raw_str.split('=>')
            input_chats = [s.strip() for s in raw_str[0].split(',')]
            output_chats = [s.strip() for s in raw_str[1].split(',')]

            dialogs = self._client.get_dialogs()

            d = {
                'input_chats': [self._get_chat_id(dialogs, c) for c in input_chats],
                'output_chats': [self._get_chat_id(dialogs, c) for c in output_chats],
            }

            logger.debug(f'Chats ID: {d}')

            self.groups.append(d)

        logger.debug('Чтение групп закончено')

    @staticmethod
    def _get_chat_id(dialogs, chat_name):
        for dialog in dialogs:
            if dialog.name == chat_name:
                return dialog.id

        logger.critical(f"Диалог {chat_name} не найден в списке диалогов вашего аккаунта")
        sys.exit(0)




