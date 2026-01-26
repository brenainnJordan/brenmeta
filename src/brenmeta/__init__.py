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

"""
"""

from Qt import QtWidgets


def validate_dependencies_v1():
    from brenmeta.core import mhCore
    from brenmeta.dna1 import mhSrc

    try:
        mhSrc.validate_plugin()
        mhSrc.validate_dna_module(force=False)

    except mhCore.MHError as err:
        res = QtWidgets.QMessageBox.question(
            None,
            "Warning",
            "Dependency error: {}\nTry force dependencies?".format(err),
        )

        if res == QtWidgets.QMessageBox.Yes:
            try:
                mhSrc.validate_dna_module(force=True)

            except mhCore.MHError as err:
                QtWidgets.QMessageBox.critical(
                    None,
                    "Error",
                    "Failed to force dependencies: {}".format(err),
                )

                return False

    return True

def validate_dependencies_v2():
    from brenmeta.core import mhCore
    from brenmeta.dna2 import mhSrc

    try:
        mhSrc.validate_plugin()
        mhSrc.validate_dna_module()
        return True

    except mhCore.MHError as err:
        QtWidgets.QMessageBox.critical(
            None,
            "Error",
            "Dependency error:\n {}".format(err),
        )

        return False

def show(version=2):
    """
    import brenmeta
    gui = brenmeta.show(version=1)
    """

    if version == 1:
        valid = validate_dependencies_v1()

        if not valid:
            return None

        from brenmeta.dna1 import mhGui

        widget = mhGui.DnaModWidget.create()
        return widget
    else:
        valid = validate_dependencies_v2()

        if not valid:
            return None

        from brenmeta.dna2 import mhGui

        widget = mhGui.DnaModWidget.create()
        return widget
