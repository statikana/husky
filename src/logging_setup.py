import logging


def begin() -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("discord").setLevel(logging.INFO)
