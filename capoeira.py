from __future__ import print_function
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import Deferred, DeferredList
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
        print("adding {} to cache".format(queryString))
        self.cache[queryString] = CacheEntry(response, interface, datetime.now())
        return response

    def deferredQuery(self, interface, paramDict):
        queryString = interface.buildQuery(paramDict)
        print("Query: " + queryString)
        if queryString in self.cache:
            cacheEntry = self.cache[queryString]
            if (cacheEntry.timestamp + timedelta(hours=24)) > datetime.now():
                return Deferred.addCallback(lambda _: cacheEntry.response)
            else:
                del self.cache[queryString]
                return (getPage(queryString).addCallbacks(callback=json.loads,
                                                          errback=stderr.write)
                                            .addCallback(lambda response: self.addToCache(queryString, interface, response)))
        else:
            return (getPage(queryString).addCallbacks(callback=json.loads,
                                                      errback=stderr.write)
                                        .addCallbacks(callback=lambda response: self.addToCache(queryString, interface, response),
                                                          errback=stderr.write)
                                        .addCallback(pprint))

    def findSimilarInArea(self):
        callbacks = DeferredList()

class CapoeiraProtocol(basic.LineReceiver):

    def lineReceived(self, line):
        self.execute(line)

    def execute(self, line):
        interface, command, args = line.split(' ')
        if interface == 'lastfm':
            from twisted.internet import reactor
            print('called {}'.format(line))
            reactor.callWhenRunning(self.factory.service.deferredQuery,
                                    self.factory.service.lastFMInterface,
                                    self.factory.service.lastFMInterface.artistGetSimilar(args))
        if interface == 'songkick':
            from twisted.internet import reactor
            print('called {}'.format(line))
            reactor.callWhenRunning(self.factory.service.deferredQuery,
                                    self.factory.service.songkickInterface,
                                    self.factory.service.songkickInterface.upcomingEvents(args))


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
