import os

from maya import cmds
from brenmeta.core import mhCore


def get_dna_data_dir(dna_version="MH.6"):

    import mh_character_assembler

    dna_data_dir = os.path.join(
        os.path.dirname(os.path.abspath(mh_character_assembler.__file__)),
        "assets",
        dna_version,
    )
    return dna_data_dir



def validate_plugin():
    """Make sure plugin is loaded with the correct version
    """
    if not cmds.pluginInfo("embeddedRL4.mll", query=True, loaded=True):
        cmds.loadPlugin("embeddedRL4.mll")

    version = cmds.pluginInfo("embeddedRL4.mll", query=True, version=True)
    version_major = int(version[0])

    if version_major != 2:
        raise mhCore.MHError("Metahuman plugin not supported: {}".format(version))

    mhCore.LOG.info("Metahuman dependencies validated")

    return True


def validate_dna_module():
    import dna

    if not hasattr(dna, "VersionInfo_getMajorVersion"):
        raise mhCore.MHError("older dna lib not supported: {}".format(dna))

    dna_version = dna.VersionInfo_getMajorVersion()

    mhCore.LOG.info("dna version: {}".format(dna_version))

    return True

