from __future__ import print_function

from twisted.application import service
from twisted.internet.defer import DeferredList, inlineCallbacks, returnValue
from twisted.web.client import getPage
from twisted.web.resource import NoResource
from twisted.web.server import Site
from txrestapi.resource import APIResource
from txrestapi.methods import GET, ALL

from config import LASTFM_API_KEY, SONGKICK_API_KEY
from lastfm import LastFMInterface
from songkick import SongkickInterface
from util import printSize, cleanString, wrap, unwrapArgs, formatResponse

import json
import os
import pickle
from sys import stderr
from datetime import timedelta
from datetime import datetime
from collections import namedtuple
import atexit


CacheEntry = namedtuple("CacheEntry", ["response", "interface", "timestamp"])
"""CacheEntry is a named tuple containing a response field, which stores the
remote API server's response, an interface field, containing which API
interface was queried, and a timestamp field which contains the time the
response was recieved"""


class CapoeiraService(service.Service):

    def __init__(self, lastFMInterface, songkickInterface):
        self.lastFMInterface = lastFMInterface
        self.songkickInterface = songkickInterface

        # load cache if it exists, else create empty dict
        if os.path.exists('./cache'):
            cacheFile = open('./cache')
            self.cache = pickle.load(cacheFile)
            cacheFile.close()
        else:
            self.cache = dict()

        atexit.register(lambda: pickle.dump(self.cache, open('./cache', 'w')))

    def addToCache(self, queryString, interface, response):
        """
        addToCache adds CacheEntry namedtuples to the cache, replacing
        currently existing cache entries if the exist
        """
        if queryString in self.cache:
            print("deleting {} from cache".format(queryString))
            del self.cache[queryString]
        print("adding {} to cache".format(queryString))
        self.cache[queryString] = CacheEntry(response,
                                             interface,
                                             datetime.now())
        return response

    @inlineCallbacks
    def deferredQuery(self, interface, paramDict):
        """
        deferredQuery constructs API calls via implemented API interfaces,
        taking care of loading responses and caching, as well as
        optionally passing the results to a consuming callback function
        """
        queryString = interface.buildQuery(paramDict)

        # if we have a recent cached version, echo and consume it
        if (queryString in self.cache) and (self.cache[queryString].timestamp
                                            + timedelta(hours=24)) > datetime.now():
            response = self.cache[queryString].response
            parsed = json.loads(response)
        else:  # otherwise, fetch, load it, cache it, and consume it
            response = yield getPage(queryString)
            printSize(response)
            try:
                parsed = json.loads(response)
            except ValueError as e:
                stderr.write(str(e))
                raise e
            self.addToCache(queryString, interface, response)
        returnValue(parsed)

    def query(self, interface, paramDict, consumingCallback=print):
        """
        query wraps deferredQuery, automatically calling the deferred
        returned by deferredQuery
        """
        from twisted.internet import reactor
        deferred = self.deferredQuery(interface, paramDict, consumingCallback)
        reactor.callWhenRunning(wrap(deferred))
        return deferred

    def lastFMQuery(self, args, fmCall):
        return self.deferredQuery(self.lastFMInterface, fmCall(**args))

    def songkickQuery(self, args, skCall):
        return self.deferredQuery(self.songkickInterface, skCall(**args))

    @inlineCallbacks
    def eventsBySimilarArtistsQuery(self, args):
        response = yield self.deferredQuery(self.lastFMInterface, self.lastFMInterface.artistGetSimilar(**args))
        try:
            artistNameList = [cleanString(response['similarartists']['artist'][index]['name'])
                              for index in range(len(response['similarartists']['artist']))]
            similarArtistList = DeferredList([self.deferredQuery(self.songkickInterface,
                                                                 self.songkickInterface.upcomingEvents(artistName))
                                              for artistName in artistNameList])
        except Exception as e:
            similarArtistList = None
        try:
            similar = yield similarArtistList.result
        except AttributeError as e:
            similar = None
        merged = self.mergeResults(similar)
        final = {'events': merged}
        final['event_count'] = len(merged)
        returnValue(formatResponse(final))

    @inlineCallbacks
    def eventsBySimilarTracksQuery(self, args):
        response = yield self.deferredQuery(self.lastFMInterface, self.lastFMInterface.trackGetSimilar(**args))
        artistNameList = [cleanString(response['similarartists']['artist'][index]['name'])
                          for index in range(len(response['similarartists']['artist']))]
        similarArtistList = DeferredList([self.deferredQuery(self.songkickInterface,
                                                             self.songkickInterface.upcomingEvents(artistName))
                                          for artistName in artistNameList])
        try:
            similar = yield similarArtistList.result
        except AttributeError as e:
            similar = None
        merged = self.mergeResults(similar)
        final = {'events': merged}
        final['event_count'] = len(merged)
        returnValue(formatResponse(final))

    def mergeResults(self, results):
        merged = []
        if not results:
            return merged
        # pull out the results from the DeferredList and remove duplicate events
        results = [callbackResult[1]['resultsPage']['results'] for callbackResult in results if callbackResult[0] is True]
        ids = set()
        for result in results:
            if 'event' in result:
                for event in result['event']:
                    if event['id'] not in ids:
                        merged.append(event)
                        ids.add(event['id'])
        return merged


class CapoeiraAPI(APIResource):

    def __init__(self, service, *args, **kwargs):
        APIResource.__init__(self, *args, **kwargs)
        self.service = service

    @inlineCallbacks
    def _makeServiceRequest(self, request, apiQuery, apiMethod):
        response = yield apiQuery(unwrapArgs(request.args), apiMethod)
        page = formatResponse(response)
        returnValue(page)

    def _checkResponse(self, response):
        if hasattr(response, 'result'):
            return response.result
        else:
            return NoResource()

    @GET('^/lastfm/artist/similar')
    def lastFMArtistSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.service.lastFMQuery,
                                            self.service.lastFMInterface.artistGetSimilar)
        return self._checkResponse(response)

    @GET('^/lastfm/track/similar')
    def lastFMTrackSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.service.lastFMQuery,
                                            self.service.lastFMInterface.trackGetSimilar)
        return self._checkResponse(response)

    @GET('^/lastfm/tag/similar')
    def lastFMTagSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.service.lastFMQuery,
                                            self.service.lastFMInterface.tagGetSimilar)
        return self._checkResponse(response)

    @GET('^/songkick/events/upcoming')
    def songkickQuery(self, request):
        response = self._makeServiceRequest(request,
                                            self.service.songkickQuery,
                                            self.service.songkickInterface.upcomingEvents)
        return self._checkResponse(response)

    @GET('^/capoeira/events/similar/artist')
    def capoeiraSimilarByArtistQuery(self, request):
        response = self.service.eventsBySimilarArtistsQuery(unwrapArgs(request.args))
        return self._checkResponse(response)

    @GET('^/capoeira/events/similar/track')
    def capoeiraSimilarByTrackQuery(self, request):
        response = self.service.eventsBySimilarTracksQuery(unwrapArgs(request.args))
        return self._checkResponse(response)

    @ALL('^/')
    def missedEndpoints(self, request):
        return "Missed the endpoints, Requst:\n{}".format(str(request))


def main():
    lastFMInterface = LastFMInterface(LASTFM_API_KEY)
    songkickInterface = SongkickInterface(SONGKICK_API_KEY)
    capoeiraService = CapoeiraService(lastFMInterface, songkickInterface)

    from twisted.internet import reactor

    api = CapoeiraAPI(capoeiraService)
    site = Site(api, timeout=None)
    port = reactor.listenTCP(8080, site)

    reactor.run()


if __name__ == '__main__':
    main()
