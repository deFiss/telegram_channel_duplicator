

class DestinationChannel:
    def __init__(self, name, channel_id):
        self._name = name
        self._channel_id = channel_id

    def name(self):
        return self._name

    def channel_id(self):
        return self._channel_id

    def __repr__(self):
        return f"{self._name} ({self._channel_id})"
