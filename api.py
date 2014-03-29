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
        base = self.baseURL
        if '_baseURL' in mergedDict:
            base = mergedDict['_baseURL']
            del mergedDict['_baseURL']
        print(base + urlencode(mergedDict))
        return base + urlencode(mergedDict)
