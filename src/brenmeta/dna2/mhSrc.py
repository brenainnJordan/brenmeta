# brenmeta metahuman DNA modification tool
#
# Copyright (C) 2025 Brenainn Jordan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

