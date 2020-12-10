import os
from loguru import logger
import sys


class ChatController:
    def __init__(self, client):
        self._client = client
        self.groups = []

        self._parse_env()

    def filter_message(self, event):
        chat_id = event.message.chat_id

        for group in self.groups:
            if chat_id in group['input_chats']:

                if group.get('white_words'):
                    if self._check_for_white_words(event, group['white_words']):
                        return group['output_chats']
                else:
                    return group['output_chats']

        return []

    def _parse_env(self):
        logger.debug('Чтение групп')
        for index in range(1, 100):
            raw_inputs = os.getenv(f'GROUP_{str(index)}_INPUTS')
            raw_outputs = os.getenv(f'GROUP_{str(index)}_OUTPUTS')
            raw_words = os.getenv(f'GROUP_{str(index)}_WORD_WHITE_LIST')

            if not raw_inputs or not raw_outputs:
                break

            logger.debug(f'Найдена группа с индексом {index}')

            input_chats = [s.strip() for s in raw_inputs.split(',')]
            output_chats = [s.strip() for s in raw_outputs.split(',')]

            dialogs = self._client.get_dialogs()

            d = {
                'input_chats': [self._get_chat_id(dialogs, c) for c in input_chats],
                'output_chats': [self._get_chat_id(dialogs, c) for c in output_chats],
            }

            if raw_words:
                d['white_words'] = [s.strip() for s in raw_words.split(',')]
                d['white_words'] = [x.replace('\\', '') for x in d['white_words']]

            logger.debug(f'Chats ID: {d}')

            self.groups.append(d)

        logger.debug('Чтение групп закончено')

    @staticmethod
    def _check_for_white_words(event, words):
        for word in words:
            if word in event.message.text:
                return True

        return False

    @staticmethod
    def _get_chat_id(dialogs, chat_name):
        for dialog in dialogs:
            if dialog.name == chat_name:
                return dialog.id

        logger.critical(f"Диалог {chat_name} не найден в списке диалогов вашего аккаунта")
        sys.exit(0)




