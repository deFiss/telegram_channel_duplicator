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

        self.input_last_message_check = {}

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

            await asyncio.sleep(self.config["delay"])

    async def _get_post_history(self, channel):
        """
        Gives the latest posts of the channel
        Doesn't duplicate posts because
        We filter messages so that only those that were
        Submitted at the beginning of the current cycle
        """

        offset = self.input_last_message_check.get(channel)

        if not offset:
            offset = 0

        history = await self.client(
            GetHistoryRequest(
                peer=channel,
                offset_id=0,
                offset_date=None,
                add_offset=0,
                limit=10,
                max_id=0,
                min_id=offset,
                hash=0,
            )
        )

        messages = history.messages[::-1]

        logger.debug(f"last cycle id for '{channel}': {self.input_last_message_check.get(channel)}")
        for m in messages:
            logger.debug(
                f"parse message with id: {m.id}, text: {m.message}, date: {m.date}"
            )

        if offset == 0:
            self.input_last_message_check[channel] = messages[-1].id
            logger.debug("skip first cycle")
            return []

        if len(messages):
            logger.debug(
                f"find new message with ids: {', '.join([str(m.id) for m in messages])}"
            )

            self.input_last_message_check[channel] = messages[-1].id
        else:
            logger.debug("new message not found")

        return messages

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
