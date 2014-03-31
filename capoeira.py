from __future__ import print_function

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from util import formatJSONResponse, formatHTMLResponse
from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language

import urllib
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredList
from twisted.python import log
from apiservice import APIService


class CapoeiraAPIService(APIService):

    def __init__(self, lastfmService, songkickService, *args, **kwargs):
        APIService.__init__(self, *args, **kwargs)
        self.lastfmService = lastfmService
        self.songkickService = songkickService

    # /capoeira/events/similar/artist
    def capoeiraSimilarByArtistQuery(self, request):
        response = self.eventsBySimilarQuery(request, self.lastfmService.lastFMArtistSimilar)
        return response

    # /capoeira/events/similar/track
    def capoeiraSimilarByTrackQuery(self, request):
        response = self.eventsBySimilarQuery(request, self.lastfmService.lastFMTrackSimilar)
        return response

    @inlineCallbacks
    def locationQuery(self, request):
        """
        Make a call to Songkick, and return the metroarea id of the first city returned
        """
        args = self._unwrapArgs(request)
        response = yield self.songkickService.songkickLocationByName(name=args['location'])
        returnValue('sk:' + str(response['resultsPage']['results']['location'][0]['metroArea']['id']))

    @inlineCallbacks
    def eventsBySimilarQuery(self, request, fmFn):
        args = self._unwrapArgs(request)
        location = 'sk:26330'
        if 'location' in args:
            try:
                location = yield self.locationQuery(request)
            except Exception as e:
                log.err(e)
            del args['location']

        response = yield fmFn(**args)

        # build list of escaped similar artist names
        artistNameList = []
        for index in range(len(response['similarartists']['artist'])):
            try:
                artistNameList.append(urllib.quote_plus(response['similarartists']['artist'][index]['name']))
            except KeyError:
                # we get a weird byte back occasionally, instead of a dict
                pass
            except Exception as e:
                log.err(e)

        # create deferred list of songkick upcoming event queries, fire off all our songkick API queries
        try:
            similarArtistList = yield DeferredList([self.songkickService.songkickUpcomingEvents(artistName,
                                                                                                location=location)
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
                                                                                                 len(callbackResult[1][
                                                                                                     'resultsPage'][
                                                                                                     'results']) > 0)]
        # remove duplicate events
        ids = set()
        for result in results:
            if 'event' in result:
                for event in result['event']:
                    if event['id'] not in ids:
                        merged.append(event)
                        ids.add(event['id'])
        return merged


class CapoeiraResource(Resource):
    def __init__(self, service):
        Resource.__init__(self)
        self.service = service
        self.resources = {
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
        # try to find acceptable response format, else fail with 406
        acceptable = self.contentNegotiator.negotiate(request.getHeader('Accept'))
        if not acceptable:
            request.setResponseCode(406)
            return ""

        # get acceptable content type and associated render function
        contentType = str(acceptable.content_type)
        renderFn = self.renderFns[contentType]
        request.setHeader("Content-Type", contentType)
        if request.path in self.resources:
            d = self.resources[request.path](request)
            d.addCallback(self._delayedRender(request, d, renderFn))
            return NOT_DONE_YET
        else:
            # TODO: better handling of path not found
            return "{}"
