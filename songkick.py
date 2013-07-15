import datetime


class SongkickInterface(object):
    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.defaultDict = {'apikey': self.apiKey}
        self.baseURL = "http://api.songkick.com/api/3.0/events.json?"

    def upcomingEvents(self,
                       artist,
                       location,
                       minDate=datetime.datetime.now().strftime("%Y-%m-%d"),
                       maxDate=(datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")):
        paramDict = {'artist_name': artist,
                     'location': location,
                     'min_date': minDate,
                     'max_date': maxDate}
        return paramDict
