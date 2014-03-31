import sys
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


def formatHTMLResponse(data):
    return """
    <html>
      <body>
        <pre>
          <code>
          {}
          </code>
        </pre>
      </body>
    </html>
    """.format(json.dumps(data, indent=4))


def formatJSONResponse(data):
    return json.dumps(data)
