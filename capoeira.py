from __future__ import print_function
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import Deferred, DeferredList, deferredGenerator
from twisted.web.client import Agent, getPage
from twisted.protocols import basic
from twisted.application import service
from txjsonrpc.web import jsonrpc

from config import LASTFM_API_KEY, LASTFM_SECRET_KEY, SONGKICK_API_KEY
from lastfm import LastFMInterface
from songkick import SongkickInterface

from pprint import pprint
import json
from sys import stderr
from datetime import timedelta
from datetime import datetime
from collections import namedtuple


CacheEntry = namedtuple("CacheEntry", ["response", "interface", "timestamp"])


class CapoeiraService(service.Service):

    def __init__(self, lastFMInterface, songkickInterface):
        self.lastFMInterface = lastFMInterface
        self.songkickInterface = songkickInterface
        self.cache = dict()

    def addToCache(self, queryString, interface, response):
        if queryString in self.cache:
            print("deleting {} from cache".format(queryString))
            del self.cache[queryString]
        print("adding {} to cache".format(queryString))
        self.cache[queryString] = CacheEntry(response, interface, datetime.now())
        return response

    def deferredQuery(self, interface, paramDict, consumingCallback=print):
        queryString = interface.buildQuery(paramDict)
        print("Query: " + queryString)
        if (queryString in self.cache) and (self.cache[queryString].timestamp + timedelta(hours=24)) > datetime.now():
            deferred = Deferred()
            deferred.callback(self.cache[queryString].response)
            return (deferred.addCallback(consumingCallback)) 
        else:
            return (getPage(queryString).addCallbacks(callback=json.loads,
                                                      errback=stderr.write)
                                        .addCallbacks(callback=lambda response: self.addToCache(queryString, interface, response),
                                                      errback=stderr.write)
                                        .addCallback(consumingCallback))


class CapoeiraProtocol(basic.LineReceiver):

    def lineReceived(self, line):
        self.execute(line)

    def execute(self, line):
        try:
            interface, args = line.split(' ')
            if interface == 'l':
                from twisted.internet import reactor
                print('called {}'.format(line))
                reactor.callWhenRunning(self.factory.service.deferredQuery,
                                        self.factory.service.lastFMInterface,
                                        self.factory.service.lastFMInterface.artistGetSimilar(args),
                                        lambda result: self.sendLine(str(result)))
            if interface == 's':
                from twisted.internet import reactor
                print('called {}'.format(line))
                reactor.callWhenRunning(self.factory.service.deferredQuery,
                                        self.factory.service.songkickInterface,
                                        self.factory.service.songkickInterface.upcomingEvents(args),
                                        lambda result: self.sendLine(str(result)))
            if interface == 'c':
                from twisted.internet import reactor
                print('called {}'.format(line))
                deferred = self.factory.service.deferredQuery(self.factory.service.lastFMInterface, self.factory.service.lastFMInterface.artistGetSimilar(args))
                deferred.addErrback(stderr.write)
                deferred.addCallback(self.deferredSimilarArtistsList)
                deferred.addCallback(lambda li: reactor.callWhenRunning(lambda _: li, None))
                deferred.addCallback(lambda _: print("derp"))
                reactor.callWhenRunning(lambda _: deferred, None)
        except Exception as err:
            print(err)

    def deferredSimilarArtistsList(self, query):
        artistNameList = [artist['name'] for artist in query['similarartists']['artist']]
        deferredList = DeferredList([getPage(self.factory.service.songkickInterface.upcomingEvents(artistName))
                             .addCallbacks(callback=print,
                                           errback=stderr.write)
                            for artistName in artistNameList])


class CapoeiraFactory(ServerFactory):

    protocol = CapoeiraProtocol

    def __init__(self, service):
        self.service = service


def main():
    lastFMInterface = LastFMInterface(LASTFM_API_KEY)
    songkickInterface = SongkickInterface(SONGKICK_API_KEY)
    capoeiraService = CapoeiraService(lastFMInterface, songkickInterface)
    factory = CapoeiraFactory(capoeiraService)
    from twisted.internet import reactor
    port = reactor.listenTCP(1100, factory, interface='localhost')
    reactor.run()


if __name__ == '__main__':
    main()
