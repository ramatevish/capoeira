

class LastFMInterface(object):

    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.defaultDict = {'api_key': self.apiKey,
                            'format': 'json'}
        self.baseURL = "http://ws.audioscrobbler.com/2.0/?"

    def artistGetSimilar(self, artist, limit=-1, autocorrect=0):
        paramDict = {'method': 'artist.getsimilar',
                     'artist': artist,
                     'limit': limit,
                     'autocorrect': autocorrect}
        return paramDict

    def trackGetSimilar(self, track, artist, limit=-1, autocorrect=0):
        paramDict = {'method': 'track.getsimilar',
                     'track': track,
                     'artist': artist,
                     'limit': limit,
                     'autocorrect': autocorrect}
        return paramDict

    def tagGetSimilar(self, tag):
        paramDict = {'method': 'tag.getsimilar',
                     'tag': tag}
        return paramDict
