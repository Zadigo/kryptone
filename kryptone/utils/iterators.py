def drop_null(items):
    for item in items:
        if item is not None:
            yield item
