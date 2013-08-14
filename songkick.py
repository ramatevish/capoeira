from api import APIInterface
import datetime


class SongkickInterface(APIInterface):

    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.defaultDict = {'baseURL': "http://api.songkick.com/api/3.0/events.json?",
                            'apikey': self.apiKey}

    def upcomingEvents(self,
                       artist,
                       location='sk:26330',
                       minDate=datetime.datetime.now().strftime("%Y-%m-%d"),
                       maxDate=(datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")):
        paramDict = {'artist_name': artist,
                     'location': location,
                     'min_date': minDate,
                     'max_date': maxDate}
        return paramDict
