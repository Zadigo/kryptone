from kryptone.signals import Signal

# Spider
post_init = Signal()
navigation = Signal()

# Databases
db_signal = Signal()


# Registry
registry_populated = Signal()
pre_init_spider = Signal()

