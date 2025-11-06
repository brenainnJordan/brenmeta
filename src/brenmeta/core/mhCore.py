import os
import sys

import logging

def ascend_path(path, levels):
    for _ in range(levels):
        path = os.path.dirname(path)
    return path

SRC_DIR = os.path.dirname(__file__)
ROOT_DIR = ascend_path(SRC_DIR, 3)
DATA_DIR = os.path.join(ROOT_DIR, "data")


def get_basic_logger(name):
    logger = logging.getLogger(name)

    if not len(logger.handlers):
        # logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        # consoleHandler.setLevel(logging.INFO)
        logger.addHandler(handler)

        formatter = logging.Formatter('%(levelname)s: %(message)s ~ %(name)s')
        logger.handlers[0].setFormatter(formatter)

        logger.propagate = False
        logger.setLevel(logging.INFO)

    return logger


LOG = get_basic_logger(__name__)


class MHError(Exception):
    def __init__(self, *args, **kwargs):
        super(MHError, self).__init__(*args, **kwargs)
