from collections import deque


class SendingMessageBuffer:
    def __init__(self, max_len):
        self._buf = deque()
        self._max_len = max_len

    def put(self, source_message, destination_channel):

        if len(self._buf) + 1 > self._max_len:
            self._buf.popleft()

        self._buf.append((source_message, destination_channel))

    def get_unedited_destination_messages(self, source_message, max_timedelta):
        return [
            m[1]
            for m in self._buf
            if m[0].id == source_message.id
            and m[0].chat_id == source_message.chat_id
            and (
                m[1].edit_date is None
                or (source_message.edit_date - m[1].edit_date) > max_timedelta
            )
        ]

    def remove_by_destination_message(self, destination_message):
        new_q = deque()

        for m in self._buf:
            if m[1] != destination_message:
                new_q.append(m)

        self._buf = new_q
