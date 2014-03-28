from twisted.application import internet, service
from capoeira import CapoeiraService, CapoeiraResource
from twisted.web.server import Site

# create application
application = application = service.Application("Capoeira")

# create CapoeiraService w/ caching
capoeiraService = CapoeiraService(False)
factory = Site(CapoeiraResource(capoeiraService))
tcpService = internet.TCPServer(8080, factory)

# add the service to the application
tcpService.setServiceParent(application)