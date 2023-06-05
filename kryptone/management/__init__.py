def execute_command_inline(argv):
    """
    Execute a command using `python manage.py`

    Parameters
    ----------

        argv (list): [file, command, ...]
    """
    utility = Utility()
    try:
        utility.call_command(argv)
    except KeyboardInterrupt:
        from kryptone.logger import logger
        logger.instance.info('Krytone was stopped')
