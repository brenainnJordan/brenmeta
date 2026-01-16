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


