from telethon import TelegramClient, events
import time
import os
from loguru import logger
from .config_controller import ConfigController
import pytz
import datetime
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio


class Client:
    def __init__(self):
        self.config = ConfigController.get_config()

        self.client = TelegramClient(
            os.path.join('session', 'account_session'),
            self.config['account_api_id'],
            self.config['account_api_hash']
        )

        logger.info('Авторизация в аккаунт')

        utc = pytz.timezone('UTC')
        self.last_message_check = datetime.datetime.now(tz=utc)

        self.command_prefix = '~!'
        self.commands = {
            'info': self._command_info,
            'add': self._command_add,
            'del': self._command_del,
            'help': self._command_help,

        }

    async def start(self):
        """
        Запуск клиента
        """
        await self.client.start(
            phone=self._get_phone,
            code_callback=self._enter_code,
            password=self._enter_password,
        )

        logger.info(f'Авторизация в аккаунт прошла успешно')

        self.client.add_event_handler(self._new_message_handler, events.NewMessage(pattern=r'.+'))
        await self.main_loop()

    async def main_loop(self):
        """
        Главный цикл
        тут обновляются конфиги,
        получается список всех новых сообщений из каждого инпут
        канала в каждой группе и рассылается по аутгруппам
        """
        while True:
            logger.debug('cycle')
            self.config = ConfigController.get_config()
            groups = await self._get_groups()

            for group in groups:
                for input_channel in group['inputs']:
                    if not input_channel:
                        continue

                    new_messages = await self._get_post_history(input_channel)

                    for output_channel in group['outputs']:
                        if not output_channel:
                            continue

                        for msg in new_messages:

                            # if words whitelist enabled
                            if group['words']:
                                if not self._check_text_entry(msg.message, group['words']):
                                    logger.debug(f"В новом сообщении {msg.id} не найдены слова из белого списка")
                                    continue

                            logger.debug(f"Отправка сообщения {msg.id} в {output_channel}")
                            await self.client.send_message(output_channel, msg)

            utc = pytz.timezone('UTC')
            self.last_message_check = datetime.datetime.now(tz=utc)

            await asyncio.sleep(self.config['delay'])

    async def _new_message_handler(self, event):
        msg_text = event.message.message

        for raw_command, command_callback in self.commands.items():
            command = self.command_prefix + raw_command

            if msg_text[:len(command)] == command:
                await command_callback(event.chat_id, msg_text.replace(command, '').strip())

    async def _command_info(self, chat_id, text):
        config = ConfigController.get_config()
        text = "**Группы:**\n\n"

        for group in config['groups']:
            group_txt = f'🔸 Имя группы: {group["name"]}\n'\
                f'🔽 Входные каналы: {", ".join(group["inputs"])}\n'\
                f'➡️ Выходные каналы: {", ".join(group["outputs"])}\n'\
                f'#️⃣ Белый список слов: {", ".join(group["words"])}\n\n'

            text += group_txt

        await self.client.send_message(chat_id, text)

    async def _command_add(self, chat_id, text):
        data = text.split('\n')
        if len(data) < 3:
            await self.client.send_message(chat_id, "❌ Неверный ввод команды")
            return

        group = {
            "name": data[0],
            "inputs": [s.strip() for s in data[1].split(',')],
            "outputs": [s.strip() for s in data[2].split(',')],
            "words": []
        }

        if len(data) >= 4:
            group["words"].extend([s.strip() for s in data[3].split(',')]),

        ConfigController.add_group(group)

        await self.client.send_message(chat_id, "✅")

    async def _command_del(self, chat_id, text):
        ConfigController.del_group(text)

        await self.client.send_message(chat_id, "✅")

    async def _command_help(self, chat_id, text):
        text = "🌐 Информация о командах\n\n"\
            f"`{self.command_prefix + 'help'}` - выводит это сообщение\n\n" \
            f"`{self.command_prefix + 'info'}` - выводит информацию о группах\n\n" \
            f"`{self.command_prefix + 'add'} [имя группы]\n[входные каналы]\n[выходные каналы]\n[белый список слов]`\n"\
            f" - добавляет группу, везде кроме названия можно перечислять через запятую\n"\
            f"**Пример:**\n`{self.command_prefix}add new group\ntest 1, test channel 2\ntest channel 3\n#tag`\n\n" \
            f"`{self.command_prefix + 'del'} [имя группы]` - удаляет группу"\


        await self.client.send_message(chat_id, text)

    async def _get_post_history(self, channel):
        """
        Отдаёт последние посты канала
        Не дублирует сообщения потому что
        Мы фильтруем сообщения что бы остались только те, которые были
        Присланы в начале текущего цикла
        """
        history = await self.client(
            GetHistoryRequest(
                peer=channel,
                offset_id=0,
                offset_date=None,
                add_offset=0,
                limit=10,
                max_id=0,
                min_id=0,
                hash=0)
        )

        messages = history.messages
        new_message = [msg for msg in messages if msg.date > self.last_message_check]

        return new_message

    @staticmethod
    def _check_text_entry(text, filters_list):
        for filter_text in filters_list:
            if filter_text in text:
                return True

        return False

    async def _get_groups(self):
        """
        Преобразовывает буквенные названия чатов в группах в айдишники
        """
        groups_list = []

        for group in self.config['groups']:
            groups_list.append(group)

            groups_list[-1]['inputs'] = [await self._get_chat_id(g) for g in groups_list[-1]['inputs']]
            groups_list[-1]['outputs'] = [await self._get_chat_id(g) for g in groups_list[-1]['outputs']]

        return groups_list

    def _get_phone(self):
        return self.config['account_phone']

    @staticmethod
    def _enter_code():
        return input('Введите код из сообщения Telegram: ')

    @staticmethod
    def _enter_password():
        return input('Введите пароль двухфакторной аутентификации: ')

    async def _get_chat_id(self, chat_name):
        async for dialog in self.client.iter_dialogs():
            if dialog.name == chat_name:
                return dialog.id

        logger.error(f"Чат с именем {chat_name} не найден в списке диалогов, он будет пропущен")
        return None


