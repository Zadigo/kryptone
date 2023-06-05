def setup():
    """Initial entrypoint that allows the configuration
    of a Krytone project by populating the application
    with the spiders"""
    from kryptone.registry import registry

    registry.populate()
