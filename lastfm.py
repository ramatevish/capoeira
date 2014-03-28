from api import APIInterface


class LastFMInterface(APIInterface):

    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.baseURL = "http://ws.audioscrobbler.com/2.0/?"
        self.defaultDict = {'api_key': self.apiKey,
                            'format': 'json'}

    def artistGetSimilar(self, artist, limit=1000, autocorrect=0):
        paramDict = {'method': 'artist.getsimilar',
                     'artist': artist,
                     'limit': limit,
                     'autocorrect': autocorrect}
        return paramDict

    def trackGetSimilar(self, track, artist, limit=1000, autocorrect=0):
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
