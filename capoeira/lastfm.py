from apiservice import APIService


class LastFMAPIService(APIService):

    def __init__(self, apiKey, *args, **kwargs):
        APIService.__init__(self, *args, **kwargs)
        self._apiKey = apiKey
        self.defaults = {'api_key': self._apiKey,
                         'format': 'json',
                         '_baseURL': "http://ws.audioscrobbler.com/2.0/?"}

    # BEGIN DEFINE API CALLS

    def _artistGetSimilar(self, artist, limit=1000, autocorrect=0):
        params = {'method': 'artist.getsimilar',
                  'artist': artist,
                  'limit': limit,
                  'autocorrect': autocorrect}
        return params

    def _trackGetSimilar(self, track, artist, limit=1000, autocorrect=0):
        params = {'method': 'track.getsimilar',
                  'track': track,
                  'artist': artist,
                  'limit': limit,
                  'autocorrect': autocorrect}
        return params

    def _tagGetSimilar(self, tag):
        params = {'method': 'tag.getsimilar',
                  'tag': tag}
        return params

    # END DEFINE API CALLS

    # /lastfm/artist/similar
    def lastFMArtistSimilar(self, *args, **kwargs):
        response = self._deferredQuery(self._artistGetSimilar(*args, **kwargs))
        return response

    # /lastfm/track/similar
    def lastFMTrackSimilar(self, *args, **kwargs):
        response = self._deferredQuery(self._trackGetSimilar(*args, **kwargs))
        return response

    # /lastfm/tag/similar
    def lastFMTagSimilar(self, *args, **kwargs):
        response = self._deferredQuery(self._tagGetSimilar(*args, **kwargs))
        return response
