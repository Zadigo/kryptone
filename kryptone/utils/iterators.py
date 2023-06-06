def drop_null(items, remove_empty_strings=True):
    for item in items:
        if remove_empty_strings and item == '':
            continue
        
        if item is not None:
            yield item


def keep_while(predicate, items):
    for item in items:
        if not predicate(item):
            continue
        yield item


def drop_while(predicate, items):
    for item in items:
        if predicate(item):
            continue
        yield item


def group_by(predicate, items):
    lhvs = []
    rhvs = []
    for item in items:
        if predicate(item):
            lhvs.append(item)
        else:
            rhvs.append(item)
    return lhvs, rhvs
