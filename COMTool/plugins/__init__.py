from . import dbg
from . import protocol
from .import terminal
# from . import graph
from . import jpgDec

pluginClasses = [dbg.Plugin, protocol.Plugin, terminal.Plugin, jpgDec.Plugin]
# pluginClasses.append(myplugin.Plugin)

builtinPlugins = {}
for c in pluginClasses:
    builtinPlugins[c.id] = c




