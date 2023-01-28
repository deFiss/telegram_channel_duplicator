class MessagePreparer:
    def __init__(self, config):
        self.config = config

    def prepare(self, message):
        pass

    def check_whitelist(self, message, whitelist):
        if not len(whitelist):
            return True

        for filter_text in whitelist:
            if filter_text.lower() in message.message.lower():
                return True

        return False
