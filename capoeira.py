from __future__ import print_function

from twisted.application import service
from twisted.internet.defer import DeferredList, inlineCallbacks, returnValue
from twisted.web.client import getPage
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.python import log

from lastfm import LastFMInterface
from songkick import SongkickInterface
from util import unwrapArgs, formatJSONResponse, formatHTMLResponse
from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language

import json
import os
import pickle
import urllib

try:
    from config import LASTFM_API_KEY, SONGKICK_API_KEY
except ImportError:
    LASTFM_API_KEY = os.environ['LASTFM_API_KEY']
    SONGKICK_API_KEY = os.environ['SONGKICK_API_KEY']

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

    def __init__(self, enableCache=False):
        self.lastFMInterface = LastFMInterface(LASTFM_API_KEY)
        self.songkickInterface = SongkickInterface(SONGKICK_API_KEY)

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
            try:
                response = yield getPage(queryString)
            except Exception as e:
                log.err("Query to {} failed: {} : {}".format(queryString, e.args, e.message))
            parsed = json.loads(response)
            if self.enableCache:  # order matters - don't add to cache if not JSON response
                self.addToCache(queryString, interface, response)
        returnValue(parsed)

    def lastFMQuery(self, args, fmFn):
        return self.deferredQuery(self.lastFMInterface, fmFn(**args))

    def songkickQuery(self, args, skFn):
        return self.deferredQuery(self.songkickInterface, skFn(**args))

    @inlineCallbacks
    def locationQuery(self, location):
        """
        Make a call to Songkick, and return the metroarea id of the first city returned
        """
        locationResponse = yield self.deferredQuery(self.songkickInterface,
                                                    self.songkickInterface.locationByName(name=location))
        returnValue('sk:' + str(locationResponse['resultsPage']['results']['location'][0]['metroArea']['id']))

    @inlineCallbacks
    def eventsBySimilarQuery(self, args, fmFn):
        location = 'sk:26330'
        if 'location' in args:
            try:
                location = yield self.locationQuery(args['location'])
            except Exception as e:
                log.err(e)
            del args['location']

        response = yield self.deferredQuery(self.lastFMInterface, fmFn(**args))

        # build list of escaped similar artist names

        artistNameList = []
        for index in range(len(response['similarartists']['artist'])):
            try:
                artistNameList.append(urllib.quote_plus(response['similarartists']['artist'][index]['name']))
            except KeyError:
                pass
            except Exception as e:
                log.err(e)

        # create deferred list of songkick upcoming event queries, fire off all our songkick API queries
        try:
            similarArtistList = yield DeferredList([self.deferredQuery(self.songkickInterface,
                                                                       self.songkickInterface.upcomingEvents(artistName,
                                                                                                             location=location))
                                                    for artistName in artistNameList])
        except Exception as e:
            log.err(e)

        # package up our results for reply
        merged = self._mergeResults(similarArtistList)
        final = {'events': merged}
        final['event_count'] = len(merged)
        returnValue(final)

    def _mergeResults(self, results):
        merged = []
        # check all of our songkick query responses, and add the results if the query was successful, and there are concerts
        results = [callbackResult[1]['resultsPage']['results'] for callbackResult in results if (callbackResult[0] and
                                                                                                 len(callbackResult[1]['resultsPage']['results']) > 0)]
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
        response = self.eventsBySimilarQuery(unwrapArgs(request.args), self.lastFMInterface.artistGetSimilar)
        return response

    # /capoeira/events/similar/track
    def capoeiraSimilarByTrackQuery(self, request):
        response = self.eventsBySimilarQuery(unwrapArgs(request.args), self.lastFMInterface.trackGetSimilar)
        return response


class CapoeiraResource(Resource):
    def __init__(self, service):
        Resource.__init__(self)
        self.service = service
        self.resources = {
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
        # function mapping for rendering response
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
            request.setResponseCode(406)
            return ""
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

#
# def main():
#     capoeiraService = CapoeiraService(True)
#     capoeiraService.startService()
#
#     from twisted.internet import reactor
#
#     factory = Site(CapoeiraResource(capoeiraService))
#     reactor.listenTCP(8080, factory)
#     reactor.run()
#
# if __name__ == '__main__':
#     main()
