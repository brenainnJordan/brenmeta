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

from maya import cmds

import dna
import dnacalib

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils

LOG = mhCore.get_basic_logger(__name__)



def find_expression_index(reader, expression, ignore_namespace=True):
    """Find matching raw control for given expression name and return index
    """
    for i in range(reader.getRawControlCount()):
        raw_control = reader.getRawControlName(i)

        if ignore_namespace:
            raw_control = raw_control.split(".")[-1]

        if raw_control == expression:
            return i

    raise mhCore.MHError("Failed to find expression: {}".format(expression))


def print_expressions(reader, ignore_namespace=True, filter=None):
    for i in range(reader.getRawControlCount()):
        raw_control = reader.getRawControlName(i)

        if ignore_namespace:
            raw_control = raw_control.split(".")[-1]

        if filter is not None:
            if isinstance(filter, str):
                filter = [filter]

            skip = False

            for i in filter:
                if i.lower() not in raw_control.lower():
                    skip = True

            if skip:
                continue

        print(raw_control)


def get_joint_attrs(reader):
    """Get a list of joint attrs that correspond to joint output indices
    """

    joint_attrs = []

    for i in range(reader.getJointCount()):
        joint = reader.getJointName(i)

        for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
            joint_attrs.append("{}.{}".format(joint, attr))

    return joint_attrs


def get_joint_defaults(reader):
    joints_attr_defaults = {}

    for i in range(reader.getJointCount()):
        joint = reader.getJointName(i)

        translation = reader.getNeutralJointTranslation(i)

        for axis, value in zip("xyz", translation):
            joints_attr_defaults["{}.t{}".format(joint, axis)] = value

            # add default rotation and scale for redundancy
            joints_attr_defaults["{}.r{}".format(joint, axis)] = 0.0
            joints_attr_defaults["{}.s{}".format(joint, axis)] = 1.0

    return joints_attr_defaults


def get_all_poses(reader, absolute=True):
    """

    """

    # get data
    joint_attrs = get_joint_attrs(reader)
    joints_attr_defaults = get_joint_defaults(reader)
    pose_names = get_pose_names(reader, extend_with_shapes=True)
    blendshape_names = get_columns_to_blendshape_channels(reader)

    # get pose values for each joint group
    poses = [
        mhCore.Pose(name=name, index=i, shape_name=shape_name)
        for i, (name, shape_name) in enumerate(zip(pose_names, blendshape_names))
    ]

    for group_index in range(reader.getJointGroupCount()):
        # get driver expressions for this joint group
        input_indices = reader.getJointGroupInputIndices(group_index)
        input_count = len(input_indices)

        # get driven attrs for this joint group
        output_indices = reader.getJointGroupOutputIndices(group_index)
        output_count = len(output_indices)
        group_attrs = [joint_attrs[i] for i in output_indices]

        # get values and add to pose data
        values = reader.getJointGroupValues(group_index)

        for column_index, input_index in enumerate(input_indices):
            pose = poses[input_index]

            for row_index, attr in enumerate(group_attrs):
                value_index = (row_index * input_count) + column_index

                value = values[value_index]

                pose.deltas[attr] = value
                pose.defaults[attr] = joints_attr_defaults[attr]

                # if absolute and attr in joints_attr_defaults:
                #     value += joints_attr_defaults[attr]
                #
                # poses[input_index].values[attr] = value

    return poses


def set_all_poses(reader, writer, pose_data, from_absolute=True):
    # validate data
    if len(pose_data) != reader.getJointColumnCount():
        raise mhCore.MHError("Joint column count ({}) != pose_data length ({})".format(
            len(pose_data), reader.getJointColumnCount()
        ))

    # get data
    joint_attrs = get_joint_attrs(reader)
    joints_attr_defaults = get_joint_defaults(reader)

    # loop through joint groups
    for group_index in range(reader.getJointGroupCount()):
        input_indices = reader.getJointGroupInputIndices(group_index)

        if not input_indices:
            print("No input indices for joint group: {}".format(group_index))
            continue

        output_indices = reader.getJointGroupOutputIndices(group_index)
        group_attrs = [joint_attrs[i] for i in output_indices]

        # get values for group
        group_values = []

        for input_index in input_indices:
            pose = pose_data[input_index]

            output_values = []

            for attr in group_attrs:
                value = pose.deltas[attr]

                # if from_absolute and attr in joints_attr_defaults:
                #     value -= joints_attr_defaults[attr]

                output_values.append(value)

            group_values.append(output_values)

        # restructure values
        values = mhMayaUtils.transpose_matrix(group_values)
        values = [i for values_i in values for i in values_i]

        # set values
        writer.setJointGroupValues(group_index, values)

    return True



def get_columns_to_blendshape_channels(reader):
    """Get list of blendshape channels associated with each joint column
    """
    blendshape_channel_names = [
        reader.getBlendShapeChannelName(i)
        for i in range(reader.getBlendShapeChannelCount())
    ]

    blendshape_channel_inputs = reader.getBlendShapeChannelInputIndices()

    columns_to_blendshapes = [None] * reader.getJointColumnCount()

    for blendshape_channel_name, joint_column in zip(blendshape_channel_names, blendshape_channel_inputs):
        columns_to_blendshapes[joint_column] = blendshape_channel_name

    return columns_to_blendshapes


def get_pose_names(reader, extend_with_shapes=True):
    """Get appropriate names for all poses (aka joint columns)
    """

    pose_names = []

    for i in range(reader.getRawControlCount()):
        pose_name = reader.getRawControlName(i)
        pose_name = pose_name.split(".")[-1]
        pose_names.append(pose_name)

    if extend_with_shapes:
        columns_to_blendshapes = get_columns_to_blendshape_channels(reader)
        pose_names.extend(columns_to_blendshapes[reader.getRawControlCount():])

    return pose_names


def get_psd_indices(reader):
    """Get a dict of psd indices with corresponding input pose indices and weights
    """
    psd_count = reader.getPSDCount()
    columns = reader.getPSDColumnIndices()
    rows = reader.getPSDRowIndices()
    values = reader.getPSDValues()

    psd_indices = {}

    for psd, pose, weight in zip(rows, columns, values):
        if psd in psd_indices:
            psd_indices[psd].append((pose, weight))
        else:
            psd_indices[psd] = [(pose, weight)]

    return psd_indices


def get_psd_poses(reader, poses, update_names=True):
    """Get a list of PSDPose objects referencing given Pose objects
    """
    psd_indices = get_psd_indices(reader)

    psd_poses = {}

    # create psd pose objects
    for psd_index, psd_data in psd_indices.items():
        psd_pose = mhCore.PSDPose()
        psd_pose.pose = poses[psd_index]

        for pose_index, weight in psd_data:
            psd_pose.input_poses.append(poses[pose_index])
            psd_pose.input_weights.append(weight)

        psd_poses[psd_index] = psd_pose

    # add input psds for 3+ way combos
    for psd_pose in psd_poses.values():
        for input_psd_pose in psd_poses.values():
            if input_psd_pose is psd_pose:
                continue

            # check if input_psd_pose has inputs that contribute to this psd
            if all([pose in psd_pose.input_poses for pose in input_psd_pose.input_poses]):
                psd_pose.input_psd_poses.append(input_psd_pose)

    if update_names:
        for psd_pose in psd_poses:
            psd_pose.update_name()

    return psd_poses
