import os
import sys

from maya import cmds

from brenmeta.core import mhCore

# IMPORTANT
# dna libs are not imported here in case of dependency issues

def get_dna_viewer_dir():
    import dna_viewer
    dna_viewer_dir = os.path.dirname(os.path.dirname(dna_viewer.__file__))
    return dna_viewer_dir


def get_dna_data_dir():
    dna_viewer_dir = get_dna_viewer_dir()
    dna_data_dir = os.path.join(dna_viewer_dir, "data")
    return dna_data_dir


def validate_plugin():
    """Make sure plugin is loaded with the correct version
    """
    if not cmds.pluginInfo("embeddedRL4.mll", query=True, loaded=True):
        cmds.loadPlugin("embeddedRL4.mll")

    version = cmds.pluginInfo("embeddedRL4.mll", query=True, version=True)

    if version[0] != "1":
        raise mhCore.MHError("Metahuman plugin not supported: {}".format(version))

    mhCore.LOG.info("Metahuman dependencies validated")

    return True


def validate_dna_module(force=True):
    import dna

    if hasattr(dna, "VersionInfo_getMajorVersion"):
        dna_version = dna.VersionInfo_getMajorVersion()

        if force:
            mhCore.remove_module_from_sys(dna)
            # try again
            import dna
            validate_dna_module(force=False)
        else:
            raise mhCore.MHError("dna lib not supported: {}".format(dna_version))

    return True


