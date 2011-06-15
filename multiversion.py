# -*- coding: utf-8 -*-
"""
    multiversion
    ~~~~~~~~~~~~

    This implements a hack to support packages in multiple versions running
    side by side in Python.  It is supported by the language and as such
    should work on any conforming Python interpreter.

    The downside is that this bypasses meta hooks so it will only be able
    to import regular modules, c extensions and modules can can be found
    with the help of a path hook.

    :copyright: (c) Copyright 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import imp
import binascii
import weakref
from types import ModuleType
import __builtin__


actual_import = __builtin__.__import__


space = imp.new_module('multiversion.space')
space.__path__ = []

sys.modules[space.__name__] = space


class ModuleProxy(ModuleType):
    """Used to proxy to an actual module.  This is needed because many
    people do `__import__` + a lookup in sys.modules.
    """

    def __init__(self, name):
        ModuleType.__init__(self, name)

    def __getattr__(self, name):
        mod = get_actual_module(self.__name__, stacklevel=2)
        if mod is None:
            raise AttributeError(name)
        return getattr(mod, name)

    def __setattr__(self, name, value):
        mod = get_actual_module(self.__name__, stacklevel=2)
        if mod is None:
            raise AttributeError(name)
        return setattr(mod, name, value)


def get_actual_module(name, stacklevel=1):
    """From the caller's view this returns the actual module that was
    requested for a given name.
    """
    globals = sys._getframe(stacklevel).f_globals
    cache_key = get_cache_key(name, globals)
    if cache_key is not None:
        full_name = '%s.%s' % (get_internal_name(cache_key), name)
        return sys.modules[full_name]


def require_version(library, version, globals=None):
    """Has to be callde at toplevel before importing a module to notify
    the multiversion system about the version that should be loaded for
    this particular library.
    """
    if globals is None:
        frm = sys._getframe(1)
        if frm.f_globals is not frm.f_locals:
            raise RuntimeError('version requirements must happen toplevel')
        globals = frm.f_globals
    mapping = globals.setdefault('__multiversion_mapping__', {})
    if library in mapping:
        raise RuntimeError('requirement already specified')
    mapping[library] = version


def version_from_module_name(module):
    """Extracts the package and version information from the given internal
    module name.  If it's not a versioned library it will return `None`.
    """
    if not module.startswith(space.__name__ + '.'):
        return None
    result = module[len(space.__name__) + 1].split('.', 1)
    if len(result) == 2 and '___' in result[1]:
        return binascii.unhexlify(result[1].rsplit('___', 1)[1])


def get_cache_key(name, globals):
    """Returns the cache key for the given module.  The globals dictionary
    is required for the magic to work.  It's used as source for the package
    name.  The cache key is in the format ``(package, version)``.  If the
    given import is not versioned it will return `None`.
    """
    mapping = globals.get('__multiversion_mapping__')
    if mapping is None:
        return
    package = name.split('.', 1)[0]
    version = mapping.get(package)
    if version is None:
        version = version_from_module_name(globals.get('__name__'))
        if version is None:
            return

    return package, version


def get_internal_name(cache_key):
    """Converts a cache key into an internal space module name."""
    package, version = cache_key
    return 'multiversion.space.%s___%s' % (package, binascii.hexlify(version))


def rewrite_import_name(name, cache_key):
    """Rewrites a whole import line according to the cache key."""
    return '%s.%s' % (get_internal_name(cache_key), name)


def version_not_loaded(cache_key):
    """Checks if the given module and version was not loaded so far."""
    internal_name = get_internal_name(cache_key)
    return sys.modules.get(internal_name) is None


def load_version(cache_key):
    """Loads a version of a module.  Will raise `ImportError` if it fails
    doing so.
    """
    fs_name = '%s-%s' % cache_key
    internal_name = get_internal_name(cache_key)
    for path_entry in sys.path:
        full_path = os.path.join(path_entry, fs_name)
        if not os.path.isdir(full_path):
            continue
        mod = imp.new_module(internal_name)
        setattr(space, internal_name.rsplit('.', 1)[1], mod)
        mod.__path__ = [full_path]
        sys.modules[mod.__name__] = mod
        return
    raise ImportError('Version %r of %r not found' % cache_key[::-1])


def version_import(name, globals=None, locals=None, fromlist=None, level=-1):
    """An import hook that performs the versioned import.  It can't work
    on the level of the regular import hooks as it's actually renaming
    imports.
    """
    if globals is None:
        globals = sys._getframe(1).f_globals
    if locals is None:
        locals = {}
    if fromlist is None:
        fromlist = []
    key = get_cache_key(name, globals)
    actual_name = name

    if key is not None:
        actual_name = rewrite_import_name(actual_name, key)
        if version_not_loaded(key):
            load_version(key)

        if not fromlist:
            fromlist = ['__name__']
    rv = actual_import(actual_name, globals, locals, fromlist, level)
    proxy = sys.modules.get(name)
    if proxy is None:
        rv.__multiversion_proxy__ = proxy = ModuleProxy(name)
        def cleanup_proxy(ref):
            try:
                sys.modules.pop(name, None)
            except (TypeError, AttributeError):
                pass
        sys.modules[name] = weakref.proxy(proxy, cleanup_proxy)
    return rv


__builtin__.__import__ = version_import
