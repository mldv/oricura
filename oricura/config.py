import yaml


class Config(dict):

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})

    def from_yaml(self, yaml_path):
        config = yaml.load(open(yaml_path))
        for k,v in config.items():
            self[k] = v
