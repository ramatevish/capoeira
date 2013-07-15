from __future__ import print_function
from config import LASTFM_API_KEY, LASTFM_SECRET_KEY, SONGKICK_API_KEY
from twisted.internet.protocol import ServerFactory
from twisted.web.client import Agent, getPage
from twisted.protocols import basic
from lastfm import LastFMInterface
from songkick import SongkickInterface
from pprint import pprint
import json
import sys


def failed(err):
    sys.stderr.write(err)


class CapoeiraService(object):

    def __init__(self, lastFMInterface, songkickInterface):
        self.lastFMInterface = lastFMInterface
        self.songkickInterface = songkickInterface

    def query(self, interface, paramDict):
        queryString = interface.buildQuery(paramDict)
        return getPage(queryString).addCallbacks(callback=json.loads, errback=failed).addCallback(pprint)


class CapoeiraProtocol(basic.LineReceiver):

    def lineReceived(self, request):
        self.getSimilarRequestRecieved(request)

    def getSimilarRequestRecieved(self, artist):
        if artist:
            from twisted.internet import reactor
            print('called {}'.format(artist))
            reactor.callWhenRunning(self.factory.service.query,
                                    self.factory.service.lastFMInterface,
                                    self.factory.service.lastFMInterface.artistGetSimilar(artist))


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
