from twisted.application import internet, service
from twisted.web.server import Site

from capoeira.lastfm import LastFMAPIService
from capoeira.songkick import SongkickAPIService
from capoeira.capoeira import CapoeiraAPIService
from capoeira.capoeira import CapoeiraResource

import memcache
from capoeira.mocks import DictionaryCache

# try to load in key values from ENV, falling back to config.py
import os
import sys
for key, keyType in [('LASTFM_API_KEY', 'str'),
                     ('LASTFM_SECRET_KEY', 'str'),
                     ('SONGKICK_API_KEY', 'str'),
                     ('PORT', 'int')]:
    try:
        exec('{} = os.environ[\'{}\']'.format(key, key))
        exec('{} = {}({})'.format(key, keyType, key))
    except TypeError as e:
        print(key)
    except KeyError as e:
        try:
            exec('from capoeira.config import {}'.format(key))
        except ImportError as e:
            sys.stderr.write("Key {} is not defined in in ENV or config.py. Exiting ...".format(key))
            sys.exit(1)

application = service.Application("api-service")
apiService = service.MultiService()
apiService.setServiceParent(application)

try:
    cache = memcache.Client(["127.0.0.1:11211"], server_max_key_length=1024)
except Exception as e:
    cache = DictionaryCache()

lastfmService = LastFMAPIService(LASTFM_API_KEY, memcacheClient=cache)
lastfmService.setServiceParent(apiService)
songkickService = SongkickAPIService(SONGKICK_API_KEY, memcacheClient=cache)
songkickService.setServiceParent(apiService)
capoeiraService = CapoeiraAPIService(songkickService=songkickService, lastfmService=lastfmService, memcacheClient=cache)
songkickService.setServiceParent(apiService)

site = Site(CapoeiraResource(capoeiraService))
tcpService = internet.TCPServer(PORT, site)

# add the service to the application
tcpService.setServiceParent(application)

