import sys
import urllib


def printSize(response):
    print("Recieved {} bytes".format(sys.getsizeof(str(response))))
    return response


def printMessage(message):
    def func(reponse):
        pr = message
        print(pr)
        return response
    return func


def cleanString(string):
    return urllib.quote_plus(string)


def tee(inp):
    print(str(inp))
    return inp


def wrap(deferred):
	return lambda _: deferred
