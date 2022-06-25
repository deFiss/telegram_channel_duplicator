import json


class ConfigController:
    @staticmethod
    def get_config():
        with open("config.json", "r", encoding="utf8") as f:
            return json.loads(f.read())

    @staticmethod
    def add_group(group):
        config = None
        with open("config.json", "r", encoding="utf8") as f:
            config = json.loads(f.read())

        config["groups"].append(group)

        with open("config.json", "w", encoding="utf8") as f:
            f.write(json.dumps(config, indent=4, ensure_ascii=False))

    @staticmethod
    def del_group(group_name):
        config = None
        with open("config.json", "r", encoding="utf8") as f:
            config = json.loads(f.read())

        new_group_list = [g for g in config["groups"] if g["name"] != group_name]
        config["groups"] = new_group_list

        with open("config.json", "w", encoding="utf8") as f:
            f.write(json.dumps(config, indent=4, ensure_ascii=False))
