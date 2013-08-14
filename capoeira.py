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
from util import printSize, printMessage, cleanString

from pprint import pprint
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
        if queryString in self.cache:
            print("deleting {} from cache".format(queryString))
            del self.cache[queryString]
        print("adding {} to cache".format(queryString))
        self.cache[queryString] = CacheEntry(response,
                                             interface,
                                             datetime.now())
        return response

    def deferredQuery(self, interface, paramDict, consumingCallback=print):
        queryString = interface.buildQuery(paramDict)
        print("query: " + queryString)
        if (queryString in self.cache) and (self.cache[queryString].timestamp
                                            + timedelta(hours=24)) > datetime.now():
            deferred = Deferred()
            deferred.callback(self.cache[queryString].response)
            return deferred.addCallback(consumingCallback)
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
        from twisted.internet import reactor
        deferred = self.factory.service.deferredQuery(interface,
                                                      paramDict,
                                                      consumingCallback)
        reactor.callWhenRunning(lambda _: deferred)
        return deferred


class CapoeiraProtocol(basic.LineReceiver):

    def lineReceived(self, line):
        self.execute(line)

    def tee(self, line):
        strLine = str(line)
        print(strLine)
        self.sendLine(strLine)
        return line

    def execute(self, line):
        try:
            interface, args = line.split(' ', 1)
            args = cleanString(args)
            if interface == 'l':
                from twisted.internet import reactor
                print('called {}'.format(line))
                reactor.callWhenRunning(self.factory.service.deferredQuery,
                                        self.factory.service.lastFMInterface,
                                        self.factory.service.lastFMInterface.artistGetSimilar(args),
                                        self.tee)
            if interface == 's':
                from twisted.internet import reactor
                print('called {}'.format(line))
                reactor.callWhenRunning(self.factory.service.deferredQuery,
                                        self.factory.service.songkickInterface,
                                        self.factory.service.songkickInterface.upcomingEvents(args),
                                        self.tee)
            if interface == 'c':
                from twisted.internet import reactor
                print('called {}'.format(line))
                deferred = self.factory.service.deferredQuery(self.factory.service.lastFMInterface,
                                                              self.factory.service.lastFMInterface.artistGetSimilar(args),
                                                              self.tee)
                deferred.addCallback(lambda response: self.deferredSimilarArtistsList(response, self.mergeResults))
                reactor.callWhenRunning(lambda _: deferred, None)

        except Exception as err:
            self.sendLine(str(err))

    def deferredSimilarArtistsList(self, query, consumingCallback):
        artistNameList = [cleanString(query['similarartists']['artist'][index]['name'])
                          for index in range(len(query['similarartists']['artist']))]
        deferredList = DeferredList([self.factory.service.deferredQuery(self.factory.service.songkickInterface,
                                                                        self.factory.service.songkickInterface.upcomingEvents(artistName),
                                                                        self.tee)
                                     for artistName in artistNameList])
        return deferredList.addCallback(consumingCallback)

    def mergeResults(self, results):
        results = [callbackResult[1]['resultsPage']['results'] for callbackResult in results if callbackResult[0] is True]
        resultsList = reduce(lambda x, y: x + list(y.itervalues()), results, [])
        print(resultsList)


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
