from telethon import TelegramClient, events
import os
from loguru import logger
from .config_controller import ConfigController
import pytz
import datetime
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio

from .destination_channel import DestinationChannel
from .source_channel import SourceChannel

SESSIONS_DIR = "sessions"


class Client:
    def __init__(self, config):
        self.config = config

        if not os.path.exists(SESSIONS_DIR):
            os.mkdir(SESSIONS_DIR)

        self.client = TelegramClient(
            os.path.join(SESSIONS_DIR, "account_session"),
            self.config["api_id"],
            self.config["api_hash"],
        )

        logger.info("Account authorization")

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

    async def get_last_messages(self, channel, min_id):
        history = await self.client(
            GetHistoryRequest(
                peer=channel.channel_id(),
                offset_id=0,
                offset_date=None,
                add_offset=0,
                limit=10,
                max_id=0,
                min_id=min_id,
                hash=0,
            )
        )

        messages = history.messages[::-1]

        return messages

    async def send_message(self, *args, **kwargs):
        return await self.client.send_message(*args, **kwargs)

    async def get_groups(self):
        """
        Converts string names of chats in groups to IDs
        """
        groups_list = []

        for group in self.config["groups"]:
            groups_list.append(group)

            groups_list[-1]["sources"] = [
                SourceChannel(g, await self._get_chat_id(g)) for g in groups_list[-1]["sources"]
            ]
            groups_list[-1]["destinations"] = [
                DestinationChannel(g, await self._get_chat_id(g)) for g in groups_list[-1]["destinations"]
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
