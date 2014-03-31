class DictionaryCache(object):

    def __init__(self, *args, **kwargs):
        self.cache = {}

    def add(self, key, value):
        self.cache[key] = value

    def get(self, key):
        return self.cache[key]


class MockRequest(object):

    def __init__(self, args=None):
        self.args = dict()
        for key, value in args.iteritems():
            self.args[key] = [value]
