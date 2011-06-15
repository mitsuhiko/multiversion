import multiversion
multiversion.require_version('mylib', '1.0')

import mylib
print 'mylib in %s: %s' % (__name__, mylib.version)

import other_module
