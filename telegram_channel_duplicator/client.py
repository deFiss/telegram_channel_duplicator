from telethon import TelegramClient, events
import os
from loguru import logger
from .config_controller import ConfigController
import pytz
import datetime
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio

SESSIONS_DIR = "sessions"


class Client:
    def __init__(self):
        self.config = ConfigController.get_config()

        if not os.path.exists(SESSIONS_DIR):
            os.mkdir(SESSIONS_DIR)

        self.client = TelegramClient(
            os.path.join(SESSIONS_DIR, "account_session"),
            self.config["api_id"],
            self.config["api_hash"],
        )

        logger.info("Account authorization")

        utc = pytz.timezone("UTC")
        self.last_message_check = datetime.datetime.now(tz=utc)

        self.command_prefix = "~!"
        self.commands = {
            "info": self._command_info,
            "add": self._command_add,
            "del": self._command_del,
            "help": self._command_help,
        }

    async def start(self):
        """
        Client launch
        """
        await self.client.start(
            phone=self._get_phone,
            code_callback=self._enter_code,
            password=self._enter_password,
        )

        logger.info(f"Account authorization was successful")

        self.client.add_event_handler(
            self._new_message_handler, events.NewMessage(pattern=r".+")
        )
        await self.main_loop()

    async def main_loop(self):
        """
        Main Loop
        configs are updated here
        get a list of all new messages from each input
        channel in each group and sent to outgroups
        """
        while True:
            logger.debug("cycle")
            self.config = ConfigController.get_config()
            groups = await self._get_groups()

            for group in groups:
                for source_channel in group["sources"]:
                    if not source_channel:
                        continue

                    new_messages = await self._get_post_history(source_channel)

                    for destination_channel in group["destinations"]:
                        if not destination_channel:
                            continue

                        if new_messages:
                            new_messages.reverse()

                        for msg in new_messages:

                            # if words whitelist enabled
                            if group["whitelist"]:
                                if not self._check_text_entry(
                                    msg.message, group["whitelist"]
                                ):
                                    logger.debug(
                                        f"Whitelisted words not found in new message {msg.id}"
                                    )
                                    continue

                            logger.debug(
                                f"Sending message {msg.id} to {destination_channel}"
                            )
                            await self.client.send_message(destination_channel, msg)

            utc = pytz.timezone("UTC")
            self.last_message_check = datetime.datetime.now(tz=utc)

            await asyncio.sleep(self.config["delay"])

    async def _new_message_handler(self, event):
        msg_text = event.message.message

        for raw_command, command_callback in self.commands.items():
            command = self.command_prefix + raw_command

            if msg_text[: len(command)] == command:
                await command_callback(
                    event.chat_id, msg_text.replace(command, "").strip()
                )

    async def _command_info(self, chat_id, text):
        config = ConfigController.get_config()
        text = "**Группы:**\n\n"

        for group in config["groups"]:
            group_txt = (
                f'🔸 Group name: {group["name"]}\n'
                f'🔽 Input channels: {", ".join(group["sources"])}\n'
                f'➡️ Output channels: {", ".join(group["outputs"])}\n'
                f'#️⃣ White list words: {", ".join(group["words"])}\n\n'
            )

            text += group_txt

        await self.client.send_message(chat_id, text)

    async def _command_add(self, chat_id, text):
        data = text.split("\n")
        if len(data) < 3:
            await self.client.send_message(chat_id, "❌ Invalid command input")
            return

        group = {
            "name": data[0],
            "inputs": [s.strip() for s in data[1].split(",")],
            "outputs": [s.strip() for s in data[2].split(",")],
            "words": [],
        }

        if len(data) >= 4:
            group["words"].extend([s.strip() for s in data[3].split(",")]),

        # delete the group with the same name if it already exists in order to replace it with a new one
        config = ConfigController.get_config()
        for g in config["groups"]:
            if g["name"] == group["name"]:
                ConfigController.del_group(g["name"])

        ConfigController.add_group(group)

        await self.client.send_message(chat_id, "✅")

    async def _command_del(self, chat_id, text):
        ConfigController.del_group(text)

        await self.client.send_message(chat_id, "✅")

    async def _command_help(self, chat_id, text):
        text = (
            "🌐 Commands Information\n\n"
            f"`{self.command_prefix + 'help'}` - outputs this message\n\n"
            f"`{self.command_prefix + 'info'}` - displays information about groups\n\n"
            f"`{self.command_prefix + 'add'} [group name]\n[input channels]\n[output channels]\n[whitelist of words]`\n"
            f" - adds a group, everywhere except the name can be listed separated by commas\n"
            f"**Example:**\n`{self.command_prefix}add new group\ntest 1, test channel 2\ntest channel 3\n#tag`\n\n"
            f"`{self.command_prefix + 'del'} [group name]` - deletes a group"
        )

        await self.client.send_message(chat_id, text)

    async def _get_post_history(self, channel):
        """
        Gives the latest posts of the channel
        Doesn't duplicate posts because
        We filter messages so that only those that were
        Submitted at the beginning of the current cycle
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
                hash=0,
            )
        )

        messages = history.messages
        new_message = [msg for msg in messages if msg.date > self.last_message_check]

        return new_message

    @staticmethod
    def _check_text_entry(text, filters_list):
        for filter_text in filters_list:
            if filter_text.lower() in text.lower():
                return True

        return False

    async def _get_groups(self):
        """
        Converts string names of chats in groups to IDs
        """
        groups_list = []

        for group in self.config["groups"]:
            groups_list.append(group)

            groups_list[-1]["inputs"] = [
                await self._get_chat_id(g) for g in groups_list[-1]["sources"]
            ]
            groups_list[-1]["outputs"] = [
                await self._get_chat_id(g) for g in groups_list[-1]["destinations"]
            ]

        return groups_list

    def _get_phone(self):
        return self.config["account_phone"]

    @staticmethod
    def _enter_code():
        return input("Enter the code from the Telegram message: ")

    @staticmethod
    def _enter_password():
        return input("Enter your two-factor authentication password: ")

    async def _get_chat_id(self, chat_name):
        async for dialog in self.client.iter_dialogs():
            if dialog.name == chat_name:
                return dialog.id

        logger.error(
            f"Chat with the name {chat_name} was not found in the list of conversations, it will be skipped"
        )
        return None
