import os
import sys

import logging

from maya import cmds

# IMPORTANT
# dna libs are not imported here in case of dependency issues

SRC_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.split(os.path.split(SRC_DIR)[0])[0]
DATA_DIR = os.path.join(ROOT_DIR, "data")


def get_dna_viewer_dir():
    import dna_viewer
    dna_viewer_dir = os.path.dirname(os.path.dirname(dna_viewer.__file__))
    return dna_viewer_dir


def get_dna_data_dir():
    dna_viewer_dir = get_dna_viewer_dir()
    dna_data_dir = os.path.join(dna_viewer_dir, "data")
    return dna_data_dir


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


def validate_plugin():
    """Make sure plugin is loaded with the correct version
    """
    if not cmds.pluginInfo("embeddedRL4.mll", query=True, loaded=True):
        cmds.loadPlugin("embeddedRL4.mll")

    version = cmds.pluginInfo("embeddedRL4.mll", query=True, version=True)

    if version[0] != "1":
        raise MHError("Metahuman plugin not supported: {}".format(version))

    LOG.info("Metahuman dependencies validated")

    return True


def remove_dna_module(dna):
    """Remove dna module from memory and sys.path so other versions can be sourced
    """

    dna_module_path = None

    for path in sys.path:
        if path in dna.__file__:
            dna_module_path = path
            break

    if not dna_module_path:
        raise MHError("Failed to find dna module path: {}".format(dna))

    LOG.warning("Removing dna module: {}".format(dna_module_path))

    sys.path.remove(dna_module_path)

    del dna
    del sys.modules["dna"]

    return True


def validate_dna_module(force=True):
    import dna

    if hasattr(dna, "VersionInfo_getMajorVersion"):
        dna_version = dna.VersionInfo_getMajorVersion()

        if force:
            remove_dna_module(dna)
            # try again
            import dna
            validate_dna_module(force=False)
        else:
            raise MHError("dna lib not supported: {}".format(dna_version))

    return True


