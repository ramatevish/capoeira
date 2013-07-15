from copy import copy


class APIInterface(object):
    def __init__(self):
        self.defaultDict = {}
        self.apiKey = None

    def buildQuery(self, paramDict):
        mergedDict = copy(self.defaultDict)
        mergedDict.update(paramDict)
        paramString = ['{}={}'.format(param, val) for param, val in mergedDict.iteritems() if param != 'baseURL']
        return mergedDict['baseURL'] + '&'.join(paramString)
