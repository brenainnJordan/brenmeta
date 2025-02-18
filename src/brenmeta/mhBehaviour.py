from maya import cmds

import dna
import dnacalib

from . import mhJoints
from . import mhCore
from . import mhMayaUtils


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

    return joints_attr_defaults


def get_all_poses(reader, absolute=True):
    """

    """

    # get data
    joint_attrs = get_joint_attrs(reader)
    joints_attr_defaults = get_joint_defaults(reader)

    # get pose values for each joint group
    pose_data = [
        {}
        for _ in range(reader.getJointColumnCount())
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
            for row_index, attr in enumerate(group_attrs):
                value_index = (row_index * input_count) + column_index

                value = values[value_index]

                if absolute and attr in joints_attr_defaults:
                    value += joints_attr_defaults[attr]

                pose_data[input_index][attr] = value

    return pose_data


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
            pose_values = pose_data[input_index]

            output_values = []

            for attr in group_attrs:
                value = pose_values[attr]

                if from_absolute and attr in joints_attr_defaults:
                    value -= joints_attr_defaults[attr]

                output_values.append(value)

            group_values.append(output_values)

        # restructure values
        values = mhMayaUtils.transpose_matrix(group_values)
        values = [i for values_i in values for i in values_i]

        # set values
        writer.setJointGroupValues(group_index, values)

    return True


def pose_joints_from_data(reader, data, expression, ignore_namespace=True, defaults=None):
    mhJoints.reset_scene_joint_xforms(reader)

    if isinstance(expression, int):
        pose_index = expression
    else:
        pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)

    pose_data = data[pose_index]

    for attr, value in pose_data.items():
        if defaults:
            if attr in defaults:
                value += defaults[attr]

        cmds.setAttr(attr, value)

    return True


def update_pose_data_from_scene(reader, data, expression, ignore_namespace=True, defaults=None):
    if isinstance(expression, int):
        pose_index = expression
    else:
        pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)

    pose_data = data[pose_index]

    for attr in pose_data.keys():
        pose_data[attr] = cmds.getAttr(attr)

        if defaults:
            if attr in defaults:
                pose_data[attr] -= defaults[attr]

    return True


def scale_pose(reader, data, expression, scale, attrs=None, ignore_namespace=True):
    # default to just scaling translation
    if attrs is None:
        attrs = ["tx", "ty", "tz"]

    pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)

    pose_data = data[pose_index]

    for pose_attr in pose_data.keys():
        attr = pose_attr.split(".")[-1]

        if attr not in attrs:
            continue

        pose_data[pose_attr] *= scale

    return True


def scale_all_poses(data, scale, attrs=None):
    # default to just scaling translation
    if attrs is None:
        attrs = ["tx", "ty", "tz"]

    for pose_data in data:
        for pose_attr in pose_data.keys():
            attr = pose_attr.split(".")[-1]

            if attr not in attrs:
                continue

            pose_data[pose_attr] *= scale

    return data


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


def get_pose_names(reader):
    """Get appropriate names for all poses (aka joint columns)
    """

    pose_names = []

    for i in range(reader.getRawControlCount()):
        pose_name = reader.getRawControlName(i)
        pose_name = pose_name.split(".")[-1]
        pose_names.append(pose_name)

    columns_to_blendshapes = get_columns_to_blendshape_channels(reader)

    pose_names.extend(columns_to_blendshapes[reader.getRawControlCount():])

    return pose_names
