from robot.running.namespace import IMPORTER

def get_libs():
    """Get imported robotframework library names."""
    return sorted(IMPORTER._library_cache._items, key=lambda _: _.name)


def get_libs_dict():
    """Get imported robotframework libraries as a name -> lib dict"""
    return {lib.name: lib for lib in IMPORTER._library_cache._items}


def match_libs(name=''):
    """Find libraries by prefix of library name, default all"""
    libs = [_.name for _ in get_libs()]
    matched = [_ for _ in libs if _.lower().startswith(name.lower())]
    return matched
