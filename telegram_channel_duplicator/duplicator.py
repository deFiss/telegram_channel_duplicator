from telegram_channel_duplicator.client import Client
from telegram_channel_duplicator.config_controller import ConfigController
from loguru import logger
import asyncio


class Duplicator:
    def __init__(self):
        self.config = ConfigController.get_config()
        self.input_last_message_check = {}

        self.client = Client(self.config)

    async def start(self):
        await self.client.start()
        await self.duplicate()

    async def duplicate(self):
        logger.info("parse conversation account list")
        groups = await self.client.get_groups()

        while True:
            logger.debug("run cycle")

            for group in groups:
                logger.debug(f"process '{group['name']}' group")
                for source_channel in group["sources"]:
                    if not source_channel:
                        continue

                    messages_history = await self.client.get_last_messages(
                        source_channel,
                        min_id=self._calc_channel_min_id(source_channel)
                    )

                    new_messages = self._filter_old_messages(source_channel, messages_history)

                    if not new_messages:
                        logger.debug(f"new messages in '{source_channel}' not found")
                        continue

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
                                        f"whitelisted words not found in new message {msg.id}"
                                    )
                                    continue

                            logger.debug(
                                f"sending message {msg.id} to {destination_channel}"
                            )
                            await self.client.send_message(destination_channel.channel_id(), msg)

            await asyncio.sleep(self.config["delay"])

    def _calc_channel_min_id(self, channel):
        channel_last_id = self.input_last_message_check.get(channel)
        if not channel_last_id:
            channel_last_id = 0

        min_id = channel_last_id - self.config["edit_message_checker_limit"]
        if min_id < 0:
            min_id = 0

        return min_id

    def _filter_old_messages(self, source_channel, messages):
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

            logger.debug(
                f"last cycle id for '{source_channel}': {new_messages[-1].id}"
            )

            source_channel.set_last_message_id(messages[-1].id)
        else:
            logger.debug("new message not found")

        return new_messages

    @staticmethod
    def _check_text_entry(text, filters_list):
        for filter_text in filters_list:
            if filter_text.lower() in text.lower():
                return True

        return False