import datetime
from apiservice import APIService


class SongkickResponse(object):

    def __init__(self, response):
        self._response = response
        self._status = response['resultsPage']['status']
        if self._status != 'ok':
            self._message = response['resultsPage']['error']['message']
        else:
            self._message = ""
            self._results = response['resultsPage']['results']

    @property
    def success(self):
        return self._status == 'ok'

    @property
    def message(self):
        return self._message

    @property
    def results(self):
        return self._results


class SongkickAPIService(APIService):

    def __init__(self, apiKey, *args, **kwargs):
        APIService.__init__(self, *args, **kwargs)
        self._apiKey = apiKey
        self.defaults = {'apikey': self._apiKey,
                         '_baseURL': 'http://api.songkick.com/api/3.0/events.json?'}

    # BEGIN DEFINE API CALLS

    def upcomingEvents(self,
                       artist,
                       location='sk:26330',
                       minDate=datetime.datetime.now().strftime("%Y-%m-%d"),
                       maxDate=(datetime.datetime.now() + datetime.timedelta(days=120)).strftime("%Y-%m-%d")):
        params = {'artist_name': artist,
                  'location': location,
                  'min_date': minDate,
                  'max_date': maxDate}
        return params

    def locationByName(self, name):
        params = {'_baseURL': 'http://api.songkick.com/api/3.0/search/locations.json?',
                  'query': name}
        return params

    # END DEFINE API CALLS

    # /songkick/events/upcoming
    def songkickUpcomingEvents(self, *args, **kwargs):
        response = self._deferredQuery(self.upcomingEvents(*args, **kwargs))
        return response

    # /songkick/location/name
    def songkickLocationByName(self, *args, **kwargs):
        response = self._deferredQuery(self.locationByName(*args, **kwargs))
        return response
