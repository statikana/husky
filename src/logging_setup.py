import logging


def begin() -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.WARNING)
