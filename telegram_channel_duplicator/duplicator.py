import datetime

from telegram_channel_duplicator.client import Client
from telegram_channel_duplicator.config_controller import ConfigController
from loguru import logger
import asyncio

from telegram_channel_duplicator.message_preparer import MessagePreparer
from telegram_channel_duplicator.sending_message_buffer import SendingMessageBuffer


class Duplicator:
    def __init__(self):
        self.config = ConfigController.get_config()

        self.groups = None

        self.client = Client(self.config)
        self.message_preparer = MessagePreparer(self.config)
        self.sending_message_buffer = SendingMessageBuffer(
            self.config["edit_message_checker_limit"]
            * sum([len(g["sources"]) for g in self.config["groups"]])
            * 5
        )

    async def start(self):
        await self.client.start()
        await self.duplicate()

    async def duplicate(self):
        logger.info("parse conversation account list")
        self.groups = await self.client.get_groups()

        while True:
            logger.debug("run cycle")

            for group in self.groups:
                logger.debug(f"process '{group['name']}' group")
                for source_channel in group["sources"]:
                    if not source_channel:
                        continue

                    messages_history = await self.client.get_last_messages(
                        source_channel, min_id=self._calc_channel_min_id(source_channel)
                    )

                    new_messages = self._filter_old_messages(
                        source_channel, messages_history
                    )

                    if not new_messages:
                        logger.debug(f"new messages in '{source_channel}' not found")
                    else:
                        await self._process_new_messages(
                            group, source_channel, new_messages
                        )

                    await self._process_edited_messages(messages_history)

            await asyncio.sleep(self.config["delay"])

    async def _process_new_messages(self, group, source_channel, new_messages):
        for destination_channel in group["destinations"]:
            if not destination_channel:
                continue

            if new_messages:
                new_messages.reverse()

            for msg in new_messages:

                if not self.message_preparer.check_whitelist(msg, group["whitelist"]):
                    logger.info(
                        f"message {msg.message} from {source_channel} not contains whitelist words, skip"
                    )
                    continue

                logger.info(
                    f"sending message {msg.message} to {destination_channel} from {source_channel}"
                )
                destination_message = await self.client.send_message(
                    destination_channel.channel_id(), msg
                )

                self.sending_message_buffer.put(
                    msg,
                    destination_message,
                )

    async def _process_edited_messages(self, messages):
        for msg in messages:
            if msg.edit_date is None:
                continue

            destination_messages = self.sending_message_buffer.get_unedited_destination_messages(
                msg,
                datetime.timedelta(seconds=int(self.config["delay"]))
            )

            logger.info(f"detected message editing in {msg.chat_id}, text: {msg.message}, copy editing")

            for dest_msg in destination_messages:
                new_msg = await self.client.client.edit_message(
                    dest_msg.chat_id, dest_msg.id, text=msg.message
                )

                self.sending_message_buffer.remove_by_destination_message(dest_msg)

                self.sending_message_buffer.put(
                    msg,
                    new_msg,
                )

    def _calc_channel_min_id(self, source_channel):
        channel_last_id = source_channel.last_message_id()

        if not channel_last_id:
            channel_last_id = 0

        min_id = channel_last_id - self.config["edit_message_checker_limit"]
        if min_id < 0:
            min_id = 0

        return min_id

    @staticmethod
    def _filter_old_messages(source_channel, messages):
        if source_channel.last_message_id() == 0:
            source_channel.set_last_message_id(messages[-1].id)
            logger.debug("skip first cycle")
            return []

        new_messages = [m for m in messages if m.id > source_channel.last_message_id()]

        for m in new_messages:
            logger.debug(
                f"parse message with id: {m.id}, text: {m.message}, date: {m.date}"
            )

        if len(new_messages):
            logger.debug(
                f"find new message with ids: {', '.join([str(m.id) for m in messages])}"
            )

            logger.debug(f"last cycle id for '{source_channel}': {new_messages[-1].id}")

            source_channel.set_last_message_id(messages[-1].id)
        else:
            logger.debug("new message not found")

        return new_messages
