# Todo, make config file generator

class Middlware:
    pass


class TraefikRule:
    pass
    def __init__(self, type):

    def express(self) -> str:
        return


class RULEMATCHERS:
    _NAMES = {
        (HEADER       := "Header")      : ('key',   'value'),
        (HEADERREGEXP := "HeaderRegexp"): ('key',   'regexp'),
        (HOSTREGEXP   := "HostRegexp")  : ('domain', ),
        (METHOD       := "Method")      : ('method', ),
        (PATH         := "Path")        : ('path', ),
        (PATHPREFIX   := "PathPrefix")  : ('prefix', ),
        (PATHREGEXP   := "PathRegexp")  : ('regexp', ),
        (QUERY        := "Query")       : ('key',   'value'),
        (QUERYREGEXP  := "QueryRegexp") : ('key',   'regexp'),
        (CLIENTIP     := "ClientIP")    : ('ip', )
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

def generate_router(
    name:str,
    rule:TraefikRule,
    rule_syntax:str = "v2"
):
