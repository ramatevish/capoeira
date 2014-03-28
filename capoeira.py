from __future__ import print_function

from twisted.application import service
from twisted.internet.defer import DeferredList, inlineCallbacks, returnValue
from twisted.web.client import getPage
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET

from config import LASTFM_API_KEY, SONGKICK_API_KEY
from lastfm import LastFMInterface
from songkick import SongkickInterface
from util import printSize, cleanString, unwrapArgs, formatJSONResponse, formatHTMLResponse
from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language

import json
import os
import pickle

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

    def __init__(self, lastFMInterface, songkickInterface, enableCache=False):
        self.lastFMInterface = lastFMInterface
        self.songkickInterface = songkickInterface

        self.enableCache = False
        if enableCache:  # load cache if it exists, else create empty dict
            self.enableCache = True
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
        if self.enableCache and (queryString in self.cache) and (self.cache[queryString].timestamp
                                                                 + timedelta(hours=24)) > datetime.now():
            response = self.cache[queryString].response
            parsed = json.loads(response)
        else:  # otherwise, fetch, load it, cache it, and consume it
            response = yield getPage(queryString)
            printSize(response)
            if self.enableCache:
                self.addToCache(queryString, interface, response)
            parsed = json.loads(response)
        returnValue(parsed)

    def lastFMQuery(self, args, fmCall):
        return self.deferredQuery(self.lastFMInterface, fmCall(**args))

    def songkickQuery(self, args, skCall):
        return self.deferredQuery(self.songkickInterface, skCall(**args))

    @inlineCallbacks
    def eventsBySimilarArtistsQuery(self, args):
        location = 'sk:26330'
        if 'location' in args:
            locationResponse = yield self.deferredQuery(self.songkickInterface,
                                                        self.songkickInterface.locationByName(name=args['location']))

            location = 'sk:' + str(locationResponse['resultsPage']['results']['location'][0]['metroArea']['id'])
            del args['location']
        response = yield self.deferredQuery(self.lastFMInterface, self.lastFMInterface.artistGetSimilar(**args))
        try:
            artistNameList = [cleanString(response['similarartists']['artist'][index]['name'])
                              for index in range(len(response['similarartists']['artist']))]
            similarArtistList = DeferredList([self.deferredQuery(self.songkickInterface,
                                                                 self.songkickInterface.upcomingEvents(artistName,
                                                                                                       location=location))
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
        returnValue(final)

    @inlineCallbacks
    def eventsBySimilarTracksQuery(self, args):
        if 'location' in args:
            location = self.deferredQuery(self.songkickInterface, self.songkickLocationByName(args['location']))
            del args['location']
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
        returnValue(final)

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

    def _makeServiceRequest(self, request, apiQueryFn, apiFn):
        return apiQueryFn(unwrapArgs(request.args), apiFn)

    # /lastfm/artist/similar
    def lastFMArtistSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.lastFMQuery,
                                            self.lastFMInterface.artistGetSimilar)
        return response

    # /lastfm/track/similar
    def lastFMTrackSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.lastFMQuery,
                                            self.lastFMInterface.trackGetSimilar)
        return response

    # /lastfm/tag/similar
    def lastFMTagSimilar(self, request):
        response = self._makeServiceRequest(request,
                                            self.lastFMQuery,
                                            self.lastFMInterface.tagGetSimilar)
        return response

    # /songkick/events/upcoming
    def songkickUpcomingEvents(self, request):
        response = self._makeServiceRequest(request,
                                            self.songkickQuery,
                                            self.songkickInterface.upcomingEvents)
        return response

    # /songkick/location/name
    def songkickLocationByName(self, request):
        response = self._makeServiceRequest(request,
                                            self.songkickQuery,
                                            self.songkickInterface.locationByName)
        return response


    # /capoeira/events/similar/artist
    def capoeiraSimilarByArtistQuery(self, request):
        response = self.eventsBySimilarArtistsQuery(unwrapArgs(request.args))
        return response

    # /capoeira/events/similar/track
    def capoeiraSimilarByTrackQuery(self, request):
        response = self.eventsBySimilarTracksQuery(unwrapArgs(request.args))
        return response

class CapoeiraResource(Resource):
    def __init__(self, service):
        Resource.__init__(self)
        self.service = service
        self.resources = {
            '/': lambda request: '<h1>Home</h1>Home page',
            '/about': lambda request: '<h1>About</h1>All about me',
            '/lastfm/track/similar': self.service.lastFMTrackSimilar,
            '/lastfm/artist/similar': self.service.lastFMArtistSimilar,
            '/lastfm/tag/similar': self.service.lastFMTagSimilar,
            '/songkick/events/upcoming': self.service.songkickUpcomingEvents,
            '/songkick/location/name': self.service.songkickLocationByName,
            '/capoeira/events/similar/artist': self.service.capoeiraSimilarByArtistQuery,
            '/capoeira/events/similar/track': self.service.capoeiraSimilarByTrackQuery
        }
        self.isLeaf = True

        # default_params is used in lieu of a defined Accept field in the header
        default_params = AcceptParameters(ContentType("text/html"), Language("en"))
        acceptable = [AcceptParameters(ContentType("text/html"), Language("en")),
                      AcceptParameters(ContentType("text/json"), Language("en")),
                      AcceptParameters(ContentType("application/json"), Language("en"))]
        self.contentNegotiator = ContentNegotiator(default_params, acceptable)
        self.renderFns = {'text/html': formatHTMLResponse,
                          'text/json': formatJSONResponse,
                          'application/json': formatJSONResponse}

    def _delayedRender(self, request, deferred, renderFn):
        def d(_):
            request.write(renderFn(deferred.result))
            request.finish()
        return d

    def render_GET(self, request):
        acceptable = self.contentNegotiator.negotiate(request.getHeader('Accept'))
        if not acceptable:
            # TODO: return 406
            contentType = 'text/html'
        else:
            contentType = str(acceptable.content_type)
        renderFn = self.renderFns[contentType]
        request.setHeader("Content-Type", contentType)
        if request.path in self.resources:
            d = self.resources[request.path](request)
            d.addCallback(self._delayedRender(request, d, renderFn))
            return NOT_DONE_YET
        else:
            return "{}"


def main():
    lastFMInterface = LastFMInterface(LASTFM_API_KEY)
    songkickInterface = SongkickInterface(SONGKICK_API_KEY)
    capoeiraService = CapoeiraService(lastFMInterface, songkickInterface, True)

    from twisted.internet import reactor

    factory = Site(CapoeiraResource(capoeiraService))
    reactor.listenTCP(8080, factory)
    reactor.run()

if __name__ == '__main__':
    main()
