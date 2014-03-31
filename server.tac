from twisted.application import internet, service
from twisted.web.server import Site

from lastfm import LastFMAPIService
from songkick import SongkickAPIService
from capoeira import CapoeiraAPIService
from capoeira import CapoeiraResource

import memcache
from mocks import DictionaryCache

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
            exec ('from config import {}'.format(key))
        except ImportError as e:
            sys.stderr("Key {} is not defined in in ENV or config.py. Exiting ...")
            sys.exit(1)

application = service.Application("api-service")
apiService = service.MultiService()
apiService.setServiceParent(application)

try:
    memcacheClient = memcache.Client(["127.0.0.1:11211"], server_max_key_length=1024)
except Exception as e:
    memcacheClient = DictionaryCache()

lastfmService = LastFMAPIService(LASTFM_API_KEY, memcacheClient=memcacheClient)
lastfmService.setServiceParent(apiService)
songkickService = SongkickAPIService(SONGKICK_API_KEY, memcacheClient=memcacheClient)
songkickService.setServiceParent(apiService)
capoeiraService = CapoeiraAPIService(songkickService=songkickService, lastfmService=lastfmService, memcacheClient=memcacheClient)
songkickService.setServiceParent(apiService)

site = Site(CapoeiraResource(capoeiraService))
tcpService = internet.TCPServer(PORT, site)

# add the service to the application
tcpService.setServiceParent(application)

