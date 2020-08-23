def is_private(name: str) -> bool:
    return name.startswith('~')


def is_global(name: str) -> bool:
    return name.startswith('/')


def make_global_ns(name: str) -> str:
    if is_private(name):
        raise ValueError('Cannot resolve private names')

    if not is_global(name):
        name = '/' + name

    if not name.endswith('/'):
        name += '/'

    return name


def canonicalize_name(name: str) -> str:
    canonical_name = '/'.join(i for i in name.split('/') if i)
    if name.startswith('/'):
        return f'/{canonical_name}'
    return canonical_name


def ns_join(ns, name):
    if is_private(name) or is_global(name):
        return name
    if ns == '~':
        return f'~{name}'
    if ns.endswith('/'):
        return ns + name
    return f'{ns}/{name}'
