import sys
import urllib
import json


def printSize(response):
    print("Recieved {} bytes".format(sys.getsizeof(str(response))))
    return response


def printMessage(message):
    def func(response):
        pr = message
        print(pr)
        return response
    return func


def cleanString(string):
    try:
        return urllib.quote_plus(string)
    except:
        return ''


def tee(inp):
    print(str(inp))
    return inp


def pipe(inp):
    print("pipe")
    return inp


def null(inp):
    return


def wrap(deferred):
    return lambda _: deferred


def unwrapArgs(argDict):
    """unwrapArgs unwraps the values in the argument dict returned by txrestapi"""
    unwrappedDict = dict()
    [unwrappedDict.setdefault(key, val[0]) for key, val in argDict.iteritems()]
    return unwrappedDict


def formatResponse(data):
    return json.dumps(data)
    # return """<html>
    #           <body>
    #           <pre>
    #           <code>
    #           {}
    #           </code>
    #           </pre>
    #           </body>
    #           </html>""".format(str(json.dumps(data, indent=4)))
