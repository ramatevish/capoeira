from copy import copy
from urllib import urlencode


class APIInterface(object):

    def __init__(self):
        self.defaultDict = {}
        self.apiKey = None
        self.baseURL = None

    def buildQuery(self, paramDict):
        mergedDict = copy(self.defaultDict)
        mergedDict.update(paramDict)
        return self.baseURL + urlencode(mergedDict)
