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
