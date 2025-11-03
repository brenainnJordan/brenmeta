from maya import cmds

import dna
import dnacalib

from . import mhJoints
from . import mhCore
from . import mhMayaUtils


class Pose(object):
    def __init__(self, name=None, index=None):
        self.index = index
        self.name = name
        self.deltas = {}
        self.defaults = {}
        self.opposite = None # TODO

    def __add__(self, other):
        """Returned summed Pose
        """
        summed_pose = Pose(name="{}_{}".format(self.name, other.name))

        summed_pose.defaults = self.defaults
        summed_pose.defaults.update(other.defaults)

        for attr, delta in self.deltas.items():
            if attr in other.deltas:
                summed_pose.deltas[attr] = delta + other.deltas[attr]
            else:
                summed_pose.deltas[attr] = delta

        for attr, delta in other.deltas.items():
            if attr in self.deltas:
                summed_pose.deltas[attr] += delta
            else:
                summed_pose.deltas[attr] = delta

        return summed_pose

    def __repr__(self):
        return "{}({}: {})".format(self.__class__.__name__, self.index, self.name)

    def get_values(self, absolute=True, blend=1.0):
        if absolute:
            values = {}

            for attr, delta in self.deltas.items():
                delta *= blend
                values[attr] = self.defaults[attr] + delta

            return values
        else:
            return self.deltas

    def pose_joints(self, blend=1.0):
        for attr, value in self.get_values(absolute=True, blend=blend).items():
            cmds.setAttr(attr, value)

        return True

    def reset_joints(self):
        for attr, value in self.defaults.items():
            cmds.setAttr(attr, value)

        return True

    def update_from_scene(self):
        for attr, default in self.defaults.items():
            value = cmds.getAttr(attr)
            self.deltas[attr] = value - default

        return True

    def scale_deltas(self, value, attrs=None):
        # default to just scaling translation
        if attrs is None:
            attrs = ["tx", "ty", "tz"]

        for pose_attr in self.deltas.keys():
            attr = pose_attr.split(".")[-1]

            if attr not in attrs:
                continue

            self.deltas[pose_attr] *= value

        return True

class PSDPose(object):
    def __init__(self):
        super(PSDPose, self).__init__()
        self.pose = None
        self.input_poses = []
        self.input_weights = []
        self.input_psd_poses = []
        self.opposite = None  # TODO

    def __repr__(self):
        return "{}({}: {}) <- [{}]".format(
            self.__class__.__name__, self.pose.index, self.pose.name,
            [pose.name for pose in self.input_poses]
        )

    def get_defaults(self):
        defaults = dict(self.pose.defaults)

        for input_pose in self.input_poses:
            for attr, default in input_pose.defaults.items():
                if attr not in defaults:
                    defaults[attr] = default

        return defaults

    def get_values(self, summed=True, absolute=True, blend=1.0):
        """
        Note the input weight is not used here (nor in the rig logic)
        it actually seems to cause issues
        """
        if not summed:
            return self.pose.get_values(absolute=absolute, blend=blend)

        summed_deltas = dict(self.pose.deltas)
        defaults = self.get_defaults()

        for input_pose in self.input_poses:
            for attr, delta in input_pose.deltas.items():
                if attr in summed_deltas:
                    summed_deltas[attr] += delta
                else:
                    summed_deltas[attr] = delta

        for input_psd_pose in self.input_psd_poses:
            for attr, delta in input_psd_pose.pose.deltas.items():
                if attr in summed_deltas:
                    summed_deltas[attr] += delta
                else:
                    summed_deltas[attr] = delta

        if absolute:
            values = {}

            for attr, default in defaults.items():
                if attr not in summed_deltas:
                    continue

                delta = summed_deltas[attr] * blend
                values[attr] = default + delta

            return values

        else:
            return summed_deltas

    def pose_joints(self, summed=True, blend=1.0):
        for attr, value in self.get_values(summed=summed, absolute=True, blend=blend).items():
            cmds.setAttr(attr, value)

        return True

    def reset_joints(self):
        for attr, value in self.get_defaults().items():
            cmds.setAttr(attr, value)

        return True

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
    pose_names = get_pose_names(reader)

    # get pose values for each joint group
    poses = [
        Pose(name=name, index=i)
        for i, name in enumerate(pose_names)
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


# def pose_joints_from_data(reader, data, expression, ignore_namespace=True, defaults=None):
#     mhJoints.reset_scene_joint_xforms(reader)
#
#     if isinstance(expression, int):
#         pose_index = expression
#     else:
#         pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)
#
#     pose = data[pose_index]
#
#     pose.pose_joints()
#
#     # for attr, value in pose.values.items():
#     #     if defaults:
#     #         if attr in defaults:
#     #             value += defaults[attr]
#     #
#     #     cmds.setAttr(attr, value)
#
#     return True


# def update_pose_data_from_scene(reader, data, expression, ignore_namespace=True, defaults=None):
#     if isinstance(expression, int):
#         pose_index = expression
#     else:
#         pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)
#
#     pose = data[pose_index]
#
#     pose.update_from_scene()
#
#     # for attr in pose.values.keys():
#     #     pose.values[attr] = cmds.getAttr(attr)
#     #
#     #     if defaults:
#     #         if attr in defaults:
#     #             pose.values[attr] -= defaults[attr]
#
#     return True


# def scale_pose(reader, data, expression, scale, attrs=None, ignore_namespace=True):
#     # default to just scaling translation
#     if attrs is None:
#         attrs = ["tx", "ty", "tz"]
#
#     pose_index = find_expression_index(reader, expression, ignore_namespace=ignore_namespace)
#
#     pose = data[pose_index]
#
#     for pose_attr in pose.values.keys():
#         attr = pose_attr.split(".")[-1]
#
#         if attr not in attrs:
#             continue
#
#         pose.values[pose_attr] *= scale
#
#     return True


# def scale_all_poses(poses, scale, attrs=None):
#     # default to just scaling translation
#     if attrs is None:
#         attrs = ["tx", "ty", "tz"]
#
#     for pose in poses:
#         for pose_attr in pose.values.keys():
#             attr = pose_attr.split(".")[-1]
#
#             if attr not in attrs:
#                 continue
#
#             pose.values[pose_attr] *= scale
#
#     return poses


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


def get_psd_indices(reader, as_names=False):
    """Get a dict of psd indices with corresponding input pose indices and weights
    """
    psd_count = reader.getPSDCount()
    columns = reader.getPSDColumnIndices()
    rows = reader.getPSDRowIndices()
    values = reader.getPSDValues()

    psd_indices = {}

    names = get_pose_names(reader)

    for psd, pose, weight in zip(rows, columns, values):
        if as_names:
            pose = names[pose]
            psd = names[psd]

        if psd in psd_indices:
            psd_indices[psd].append((pose, weight))
        else:
            psd_indices[psd] = [(pose, weight)]

    return psd_indices

def get_psd_poses(reader, poses):
    """Get a list of PSDPose objects referencing given Pose objects
    """
    psd_indices = get_psd_indices(reader)

    psd_poses = {}

    # create psd pose objects
    for psd_index, psd_data in psd_indices.items():
        psd_pose = PSDPose()
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

        # if psd_pose.input_psd_poses:
        #     print("psd pose input psd poses found: {} ({})".format(
        #         psd_pose.pose.name,
        #         [pose.pose.name for pose in psd_pose.input_psd_poses]
        #     ))

    return psd_poses
