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

import dna
import dnacalib2

from maya import cmds
from maya.api import OpenMaya

from brenmeta.core import mhCore

LOG = mhCore.get_basic_logger(__name__)

def get_joint_index(reader, joint_name):
    for i in range(reader.getJointCount()):
        if reader.getJointName(i) == joint_name:
            return i
    return None


def reset_scene_joint_xforms(reader, err=False):
    for i in range(reader.getJointCount()):
        joint = reader.getJointName(i)

        if not cmds.objExists(joint):
            if err:
                raise mhCore.MHError("Joint not found: {}".format(joint))

        translation = reader.getNeutralJointTranslation(i)

        cmds.xform(
            joint, translation=translation, rotation=(0, 0, 0)
        )

    return True


def update_joint_neutral_xforms(calib_reader, verbose=False, err=False):
    joint_translations = []
    joint_rotations = []

    for i in range(calib_reader.getJointCount()):
        joint_name = calib_reader.getJointName(i)

        if not cmds.objExists(joint_name):
            msg = "Joint not found: {}".format(joint_name)

            if err:
                raise mhCore.MHError(msg)
            else:
                cmds.warning(msg)

            translation = calib_reader.getNeutralJointTranslation(i)
            rotation = calib_reader.getNeutralJointRotation(i)
        else:
            if verbose:
                LOG.info("Updating joint: {}".format(joint_name))

            translation = cmds.xform(joint_name, query=True, translation=True)
            rotation = cmds.joint(joint_name, query=True, orientation=True)

        joint_translations.append(translation)
        joint_rotations.append(rotation)

    translations_cmd = dnacalib2.SetNeutralJointTranslationsCommand(joint_translations)
    rotations_cmd = dnacalib2.SetNeutralJointRotationsCommand(joint_rotations)

    commands = dnacalib2.CommandSequence()
    commands.add(translations_cmd)
    commands.add(rotations_cmd)
    commands.run(calib_reader)

    return True


def update_joint_list(calib_reader, verbose=False):
    """Remove any joints in the reader that don't exist in the scene
    """
    indices_to_remove = []

    for i in range(calib_reader.getJointCount()):
        joint_name = calib_reader.getJointName(i)

        if not cmds.objExists(joint_name):
            if verbose:
                LOG.info("Removing joint from dna: {}".format(joint_name))

            indices_to_remove.append(i)

    commands = dnacalib2.CommandSequence()

    for i in reversed(indices_to_remove):
        command = dnacalib2.RemoveJointCommand(i)
        commands.add(command)

    commands.run(calib_reader)

    return True


def merge_joint_neutral_xforms(src_calib_reader, dst_calib_reader):
    joint_translations = []
    joint_rotations = []

    for dst_index in range(dst_calib_reader.getJointCount()):
        joint_name = dst_calib_reader.getJointName(dst_index)

        src_index = get_joint_index(src_calib_reader, joint_name)

        if src_index is None:
            LOG.warning("joint not found in src reader: {}".format(joint_name))

            translation = dst_calib_reader.getNeutralJointTranslation(dst_index)
            rotation = dst_calib_reader.getNeutralJointRotation(dst_index)
        else:
            LOG.info("Updating joint: {}".format(joint_name))

            translation = src_calib_reader.getNeutralJointTranslation(src_index)
            rotation = src_calib_reader.getNeutralJointRotation(src_index)

        joint_translations.append(translation)
        joint_rotations.append(rotation)

    translations_cmd = dnacalib2.SetNeutralJointTranslationsCommand(joint_translations)
    rotations_cmd = dnacalib2.SetNeutralJointRotationsCommand(joint_rotations)

    commands = dnacalib2.CommandSequence()
    commands.add(translations_cmd)
    commands.add(rotations_cmd)
    commands.run(dst_calib_reader)

    return True
