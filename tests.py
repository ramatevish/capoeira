# coding=utf-8
import unittest
from capoeira.mocks import DictionaryCache, MockRequest
from capoeira.capoeira import CapoeiraAPIService
from capoeira.lastfm import LastFMAPIService
from capoeira.songkick import SongkickAPIService, SongkickResponse
import memcache


class TestCapoeira(unittest.TestCase):
    def setUp(self, cache=None):
        if cache == 'mock':
            self.cache = DictionaryCache()
        elif cache == 'memcached':
            self.cache = memcache.Client(['127.0.0.1:12221'])
        else:
            self.cache = None

        self.lastfmService = LastFMAPIService("abcdefg", memcacheClient=self.cache)
        self.songkickService = SongkickAPIService("hijklmn", memcacheClient=self.cache)
        self.capoeiraService = CapoeiraAPIService(songkickService=self.songkickService,
                                                  lastfmService=self.lastfmService,
                                                  memcacheClient=self.cache)


class TestSongkickFunctionality(TestCapoeira):
    def setUp(self):
        super(TestSongkickFunctionality, self).setUp(cache='mock')

        self.songkickResponses = {}

        def _fakeSongkickDeferredQuery(parameters):
            uri = self.songkickService._buildQuery(parameters)
            return self.songkickResponses[uri]

        self.songkickService._deferredQuery = _fakeSongkickDeferredQuery

        self.lastFMResponses = {}

        def _fakeLastFMDeferredQuery(parameters):
            uri = self.lastfmService._buildQuery(parameters)
            return self.lastFMResponses[uri]

        self.lastfmService._deferredQuery = _fakeLastFMDeferredQuery

    def testSongkickInvalidAPIKey(self):
        self.songkickResponses[
            'http://api.songkick.com/api/3.0/search/locations.json?query=los+angeles&apikey=hijklmn'] = \
            {
                "resultsPage": {
                    "status": "error",
                    "error": {
                        "message": "Invalid or missing apikey"
                    }
                }
            }
        result = SongkickResponse(self.songkickService.songkickLocationByName(name='los angeles'))
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Invalid or missing apikey")


    def testLocationQueryValidLocation(self):
        # query to find metro area id
        self.songkickResponses[
            'http://api.songkick.com/api/3.0/search/locations.json?query=los+angeles&apikey=hijklmn'] = \
            {'resultsPage': {'page': 1,
                             'perPage': 50,
                             'results': {'location': [{'city': {'country': {'displayName': 'US'},
                                                                'displayName': 'Los Angeles',
                                                                'lat': 34.0862,
                                                                'lng': -118.376,
                                                                'state': {'displayName': 'CA'}},
                                                       'metroArea': {'country': {'displayName': 'US'},
                                                                     'displayName': 'Los Angeles',
                                                                     'id': 17835,
                                                                     'lat': 34.0862,
                                                                     'lng': -118.376,
                                                                     'state': {'displayName': 'CA'},
                                                                     'uri': 'http://www.songkick.com/metro_areas/17835-us-los-angeles?utm_source=21294&utm_medium=partner'}},
                                                      {'city': {'country': {'displayName': 'Chile'},
                                                                'displayName': 'Los \xc3\x81ngeles',
                                                                'lat': -37.4667,
                                                                'lng': -72.35},
                                                       'metroArea': {'country': {'displayName': 'Chile'},
                                                                     'displayName': 'Los \xc3\x81ngeles',
                                                                     'id': 27512,
                                                                     'lat': -37.4667,
                                                                     'lng': -72.35,
                                                                     'uri': 'http://www.songkick.com/metro_areas/27512-chile-los-angeles?utm_source=21294&utm_medium=partner'}}]},
                             'status': 'ok',
                             'totalEntries': 2}}
        # test capoeira's location query
        request = MockRequest({'location': 'los angeles'})
        result = self.capoeiraService.locationQuery(request).result
        self.assertEqual(result, 'sk:17835')


    def testLocationQueryInvalidLocation(self):
        self.songkickResponses['http://api.songkick.com/api/3.0/search/locations.json?query=narnia&apikey=hijklmn'] = \
            {
                "resultsPage": {
                    "status": "ok",
                    "results": {},
                    "perPage": 50,
                    "page": 1,
                    "totalEntries": 0
                }
            }
        request = MockRequest({'location': 'narnia'})
        result = self.capoeiraService.locationQuery(request).result
        self.assertEqual(result, 'sk:26330')

    def testSongkickUpcomingEventsSuccess(self):
        self.songkickResponses['http://api.songkick.com/api/3.0/events.json?apikey=hijklmn&max_date=2014-07-29'
                               '&min_date=2014-03-31&artist_name=Tiga&location=sk%3A26330'] = {
            "resultsPage": {
                "status": "ok",
                "results": {
                    "event": [{
                        "type": "Concert",
                        "status": "ok",
                        "performance": [{
                            "billing": "headline",
                            "artist": {
                                "identifier": [{
                                    "mbid": "58e5332d-383e-414c-9917-776d7b1493a2",
                                    "href": "http://api.songkick.com/api/3.0/artists/mbid:58e5332d-383e-414c-9917-776d7b1493a2.json"
                                }, {
                                    "mbid": "6ee8934a-6970-4dce-b2ac-53a93a41af21",
                                    "href": "http://api.songkick.com/api/3.0/artists/mbid:6ee8934a-6970-4dce-b2ac-53a93a41af21.json"
                                }],
                                "uri": "http://www.songkick.com/artists/242571-tiga?utm_source=21294&utm_medium=partner",
                                "displayName": "Tiga",
                                "id": 242571
                            },
                            "billingIndex": 1,
                            "displayName": "Tiga",
                            "id": 39406889
                        }, {
                            "billing": "support",
                            "artist": {
                                "identifier": [{
                                    "mbid": "e425b041-c28a-4ae8-9d5c-997890433cd4",
                                    "href": "http://api.songkick.com/api/3.0/artists/mbid:e425b041-c28a-4ae8-9d5c-997890433cd4.json"
                                }],
                                "uri": "http://www.songkick.com/artists/423930-green-velvet?utm_source=21294&utm_medium=partner",
                                "displayName": "Green Velvet",
                                "id": 423930
                            },
                            "billingIndex": 2,
                            "displayName": "Green Velvet",
                            "id": 39406894
                        }],
                        "venue": {
                            "lat": 37.778048,
                            "metroArea": {
                                "country": {
                                    "displayName": "US"
                                },
                                "uri": "http://www.songkick.com/metro_areas/26330-us-sf-bay-area?utm_source=21294&utm_medium=partner",
                                "id": 26330,
                                "state": {
                                    "displayName": "CA"
                                },
                                "displayName": "SF Bay Area"
                            },
                            "lng": -122.405681,
                            "uri": "http://www.songkick.com/venues/5670-1015-folsom?utm_source=21294&utm_medium=partner",
                            "displayName": "1015 Folsom",
                            "id": 5670
                        },
                        "start": {
                            "time": "22:00:00",
                            "date": "2014-04-16",
                            "datetime": "2014-04-16T22:00:00-0800"
                        },
                        "popularity": 0.038124,
                        "location": {
                            "lat": 37.778048,
                            "lng": -122.405681,
                            "city": "San Francisco, CA, US"
                        },
                        "ageRestriction": None,
                        "uri": "http://www.songkick.com/concerts/19838379-tiga-at-1015-folsom?utm_source=21294&utm_medium=partner",
                        "id": 19838379,
                        "displayName": "Tiga with Green Velvet at 1015 Folsom (April 16, 2014)"
                    }]
                },
                "perPage": 50,
                "page": 1,
                "totalEntries": 1
            }
        }
        result = SongkickResponse(self.songkickService.songkickUpcomingEvents(artist='Tiga'))
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
