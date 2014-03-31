from copy import copy
import json
from urllib import urlencode
from twisted.application import service
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python import log
from twisted.web.client import getPage


class APIService(service.Service):
    enableCache = False

    def __init__(self, memcacheClient=None):
        self.defaults = {}

        if memcacheClient:
            self.cache = memcacheClient
            self.enableMemcache = True

    def _addToCache(self, query, response):
        """
        _addToCache adds k/v pair to memcache. TODO: configure TTL on cache entries
        """
        log.msg("adding {} to cache".format(query))
        self.cache.add(query, response)
        return response

    def _buildQuery(self, params):
        merged = copy(self.defaults)
        merged.update(params)
        base = merged['_baseURL']
        del merged['_baseURL']
        return base + urlencode(merged)

    def _unwrapArgs(self, request):
        """
        _unwrapArgs unwraps the values in the argument dict passed in by a request
        """
        argDict = request.args
        unwrappedDict = dict()
        [unwrappedDict.setdefault(key, val[0]) for key, val in argDict.iteritems()]
        return unwrappedDict

    @inlineCallbacks
    def _deferredQuery(self, parameters):
        """
        _deferredQuery constructs API calls via implemented API interfaces, taking care of loading responses and caching
        """
        query = self._buildQuery(parameters)

        response, parsed = None, None
        if self.enableMemcache:
            response = self.cache.get(query)
        try:
            if not response:  # if we couldn't get response from the cache
                response = yield getPage(query)
            parsed = json.loads(response)
            if self.enableMemcache:
                # TODO: check how long this actually takes - most likely a blocking call
                self._addToCache(query, response)
        except ValueError as e:
            log.err("Response was not valid JSON: " + str(response))
        except Exception as e:
            log.err("Query to {} failed for unknown reason: {}".format(query, e))
            returnValue(dict())
        returnValue(parsed)
