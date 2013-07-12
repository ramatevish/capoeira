from __future__ import print_function
from twisted.internet.protocol import ServerFactory
from twisted.web.client import Agent, getPage
from twisted.internet.defer import Deferred
from twisted.protocols import basic
from config import API_KEY, SECRET_KEY
from copy import copy
import json
import sys


def failed(err):
    print >>sys.stderr, 'failed:', err
    errors.append(err)


class LastFMQueryService(object):
    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.defaultDict = {'api_key': self.apiKey,
                            'format': 'json'}
        self.baseUrl = "http://ws.audioscrobbler.com/2.0/?"

    def buildQuery(self, paramDict):
        mergedDict = copy(self.defaultDict)
        mergedDict.update(paramDict)
        paramString = ['{}={}'.format(param, val) for param, val in mergedDict.iteritems()]
        return self.baseUrl + '&'.join(paramString)

    def query(self, paramDict):
        queryString = self.buildQuery(paramDict)
        return getPage(queryString).addCallbacks(callback=json.loads, errback=failed).addCallback(print)
    
    def artistGetSimilar(self, artist, limit=-1, autocorrect=0):
        paramDict = {'method': 'artist.getSimilar',
                     'artist': artist,
                     'limit': limit,
                     'autocorrect': autocorrect}
        return self.query(paramDict)    

    def artistGetInfo(self, artist, lang='en', autocorrect=0):
        paramDict = {'method': 'artist.getInfo',
                     'artist': artist,
                     'lang': lang,
                     'autocorrect': autocorrect}
        return self.query(paramDict)

class CapoeiraProtocol(basic.LineReceiver):

    def lineReceived(self, request):
        self.getSimilarRequestRecieved(request)

    def getSimilarRequestRecieved(self, artist):
        from twisted.internet import reactor
        print('called {}'.format(artist))
        reactor.callWhenRunning(self.factory.service.getSimilarArtists, artist)

class CapoeiraFactory(ServerFactory):

    protocol = CapoeiraProtocol

    def __init__(self, service):
        self.service = service

def main():
    lastFMQueryService = LastFMQueryService(API_KEY)
    factory = CapoeiraFactory(lastFMQueryService)
    from twisted.internet import reactor
    port = reactor.listenTCP(1100, factory, interface='localhost')

    reactor.run()


if __name__ == '__main__':
    main()
