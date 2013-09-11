from __future__ import print_function

from twisted.application import service
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import Deferred, DeferredList
from twisted.protocols import basic
from twisted.web.client import getPage
from twisted.web.server import Site
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

from config import LASTFM_API_KEY, LASTFM_SECRET_KEY, SONGKICK_API_KEY
from lastfm import LastFMInterface
from songkick import SongkickInterface
from util import printSize, printMessage, cleanString, tee, wrap

import json
import os
import pickle
from sys import stderr
from datetime import timedelta
from datetime import datetime
from collections import namedtuple
import atexit


CacheEntry = namedtuple("CacheEntry", ["response", "interface", "timestamp"])


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

    def deferredQuery(self, interface, paramDict, consumingCallback=print):
        """
        deferredQuery constructs API calls via implemented API interfaces,
        taking care of loading JSON responses and caching, as well as
        optionally passing the results to a consuming callback function
        """
        queryString = interface.buildQuery(paramDict)
        print("query: " + queryString)

        # if we have a recent cached version, echo and consume it
        if (queryString in self.cache) and (self.cache[queryString].timestamp
                                            + timedelta(hours=24)) > datetime.now():
            deferred = Deferred()
            deferred.callback(self.cache[queryString].response)
            return deferred.addCallback(consumingCallback)
        # otherwise, fetch, load it, cache it, and consume it
        else:
            return (getPage(queryString).addCallback(printSize)
                                        .addCallbacks(callback=json.loads,
                                                      errback=stderr.write)
                                        .addCallbacks(callback=lambda response:
                                                        self.addToCache(queryString,
                                                                        interface,
                                                                        response),
                                                      errback=stderr.write)
                                        .addCallback(consumingCallback))

    def query(self, interface, paramDict, consumingCallback=print):
        """
        query wraps deferredQuery, automatically calling the deferred
        returned by deferredQuery
        """
        from twisted.internet import reactor
        deferred = self.deferredQuery(interface,
                                      paramDict,
                                      consumingCallback)
        reactor.callWhenRunning(wrap(deferred))
        return deferred

    def lastFMQuery(self, request):
        print(request.args)
        artist = request.args['artist'][0]
        print('lastFMQuery: {}'.format(artist))
        deferred = self.deferredQuery(self.lastFMInterface,
                                      self.lastFMInterface.artistGetSimilar(artist),
                                      tee)
        return deferred

    def songkickQuery(self, args):
        print("songkickQuery: {}".format(args))
        deferred =  self.deferredQuery(self.songkickInterface,
                                       self.songkickInterface.upcomingEvents(args),
                                       tee)
        return deferred

    def combineQuery(self, args):
        print("combineQuery: {}".format(args))
        deferred = self.deferredQuery(self.lastFMInterface,
                                      self.lastFMInterface.artistGetSimilar(args),
                                      tee)
        deferred.addCallback(lambda response: self.deferredSimilarArtistsList(response, self.mergeResults))
        return deferred

    def deferredSimilarArtistsList(self, query, consumingCallback):
        artistNameList = [cleanString(query['similarartists']['artist'][index]['name'])
                          for index in range(len(query['similarartists']['artist']))]
        deferredList = DeferredList([self.deferredQuery(self.songkickInterface,
                                                        self.songkickInterface.upcomingEvents(artistName),
                                                        tee)
                                     for artistName in artistNameList])
        return deferredList.addCallback(consumingCallback)

    def mergeResults(self, results):
        results = [callbackResult[1]['resultsPage']['results'] for callbackResult in results if callbackResult[0] is True]
        resultsList = reduce(lambda x, y: x + list(y.itervalues()), results, [])
        print(resultsList)


class CapoeiraAPI(APIResource):

    def __init__(self, service, *args, **kwargs):
        APIResource.__init__(self, *args, **kwargs)
        self.service = service

    @POST('^/lastfm/similar_artists')
    def lastFMQuery(self, request):
        return str(self.service.lastFMQuery(request).result)

    @POST('^/songkick/upcoming_events')
    def songkickQuery(self, request):
        return str(self.service.songkickQuery(request).result)

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
