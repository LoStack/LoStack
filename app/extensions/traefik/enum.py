# Todo, make config file generator

class MATCHERS:
    HEADER = "Header"
    HEADERREGEXP = "HeaderRegexp"
    HOSTREGEXP = "HostRegexp"
    METHOD = "Method"
    PATH = "Path"
    PATHPREFIX = "PathPrefix"
    PATHREGEXP = "PathRegexp"
    QUERY = "Query"
    QUERYREGEXP = "QueryRegexp"
    CLIENTIP = "ClientIP"

    ARGS = {
        "HEADER" : ('key', 'value'),
        "HEADERREGEXP" : ('key', 'regexp'),
        "HOSTREGEXP" : ('domain'),
        "METHOD" : ('method'),
        "PATH" : ('path'),
        "PATHPREFIX" : ('prefix'),
        "PATHREGEXP" : ('regexp'),
        "QUERY" : ('key', 'value'),
        "QUERYREGEXP" : ('key', 'regexp'),
        "CLIENTIP" : ('ip')
    }


class TraefikRule:
    matcher
    domain
    ip
    key
    method
    path
    prefix
    regexp
    value
    def express():
        pass

def generate_config():
    config = {
        "http": {
            "middlewares": {},
            "services": {},
            "routers": {}
        }
    }