# Copyright Least Authority Enterprises.
# See LICENSE for details.

"""
The command-line interface.

Theory of Operation
===================

#. Convert command line arguments to structured configuration, supplying defaults where necessary.
#. Construct the top-level kubetop service from the configuration.
#. Run the Twisted reactor.
"""

from sys import __stdout__ as outfile

from yaml import safe_load

from itertools import repeat
from os.path import expanduser
import os

from twisted.python.usage import Options
from twisted.python.filepath import FilePath

from ._twistmain import TwistMain
from ._runmany import run_many_service
from ._textrenderer import Sink, kubetop

DEFAULT_CONFIG = os.getenv('KUBECONFIG', "~/.kube/config")
DEFAULT_CONFIG_FILE_PATH = FilePath(expanduser(DEFAULT_CONFIG))

def current_context(config_path):
    with config_path.open() as cfg:
        return safe_load(cfg)[u"current-context"]


class KubetopOptions(Options):
    optParameters = [
        ("config", None, DEFAULT_CONFIG, "The path to the kubectl config to use."),
        ("context", None, None, "The kubectl context to use. If not set, this will default to the 'current-context' of the 'config'."),
        ("interval", None, 3.0, "The number of seconds between iterations.", float),
        ("iterations", None, None, "The number of iterations to perform.", int),
    ]

    def postOptions(self):
        # Calculate the context as a post action instead of setting a default value in optParameters since
        # kubetop should use/show the context of any overridden 'config'
        self['context'] = current_context(FilePath(expanduser(self['config'])))



def fixed_intervals(interval, iterations):
    if iterations is None:
        return repeat(interval)
    return repeat(interval, iterations)



def makeService(main, options):
    from twisted.internet import reactor

    # _topdata imports txkube and treq, both of which import
    # twisted.web.client, which imports the reactor, which installs a default.
    # That breaks TwistMain unless we delay it until makeService is called.
    from ._topdata import make_source

    f = lambda: kubetop(reactor, s, Sink.from_file(outfile))

    s = make_source(reactor, FilePath(expanduser(options["config"])), options["context"])
    return run_many_service(
        main, reactor, f,
        fixed_intervals(options["interval"], options["iterations"]),
    )


main = TwistMain(KubetopOptions, makeService)
