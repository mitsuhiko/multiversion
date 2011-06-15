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
import __builtin__


actual_import = __builtin__.__import__


space = imp.new_module('multiversion.space')
space.__path__ = []
sys.modules[space.__name__] = space


def require_version(library, version):
    """Has to be callde at toplevel before importing a module to notify
    the multiversion system about the version that should be loaded for
    this particular library.
    """
    frm = sys._getframe(1)
    if frm.f_globals is not frm.f_locals:
        raise RuntimeError('version requirements must happen toplevel')
    mapping = frm.f_globals.setdefault('__multiversion_mapping__', {})
    if library in mapping:
        raise RuntimeError('requirement already specified')
    mapping[library] = version


def version_from_module_name(module):
    if not module.startswith(space.__name__ + '.'):
        return None
    result = module[len(space.__name__) + 1].split('.', 1)
    if len(result) == 2 and '___' in result[1]:
        return binascii.unhexlify(result[1].rsplit('___', 1)[1])


def get_cache_key(name, globals):
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
    package, version = cache_key
    return 'multiversion.space.%s___%s' % (package, binascii.hexlify(version))


def rewrite_import_name(name, cache_key):
    return '%s.%s' % (get_internal_name(cache_key), name)


def version_not_loaded(cache_key):
    internal_name = get_internal_name(cache_key)
    return sys.modules.get(internal_name) is None


def load_version(cache_key):
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
    if globals is None:
        globals = {}
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
    return actual_import(actual_name, globals, locals, fromlist, level)


__builtin__.__import__ = version_import
