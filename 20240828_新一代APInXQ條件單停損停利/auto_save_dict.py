import json

class AutoSaveDict(dict):
    def __init__(self, filename, *args, **kwargs):
        self.filename = filename
        super().__init__(*args, **kwargs)
        self.load()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.save()

    def pop(self, key, default=None):
        result = super().pop(key, default)
        self.save()
        return result

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.save()

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(dict(self), f)

    def load(self):
        try:
            with open(self.filename, 'r') as f:
                self.update(json.load(f))
        except FileNotFoundError:
            pass