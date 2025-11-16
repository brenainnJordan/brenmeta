from maya import cmds

import dna
import dnacalib
import dna_viewer

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils

LOG = mhCore.get_basic_logger(__name__)


class Pose(object):
    def __init__(self, name=None, index=None, shape_name=None):
        self.index = index
        self.name = name
        self.shape_name = shape_name
        self.deltas = {}
        self.defaults = {}
        self.opposite = None  # TODO

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

    def get_display_name(self, index=True, blendshape=True):
        display_name = ""

        if index:
            display_name += "{}: ".format(self.index)

        if self.name:
            display_name += "{}".format(self.name)

        if blendshape:
            display_name += " ({})".format(self.shape_name)

        return display_name

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

    def scale_deltas(self, value, attrs=None, joints=None):
        # default to just scaling translation
        if attrs is None:
            attrs = ["tx", "ty", "tz"]

        for pose_attr in self.deltas.keys():
            joint, attr = pose_attr.split(".")

            if attr not in attrs:
                continue

            if joints:
                if joint not in joints:
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

    def get_all_input_poses(self):
        poses = set(self.input_poses)

        for input_psd_pose in self.input_psd_poses:
            poses.update(input_psd_pose.get_all_input_poses())

        return poses


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
        Pose(name=name, index=i, shape_name=shape_name)
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


def get_psd_indices(reader):  # , as_names=False):
    """Get a dict of psd indices with corresponding input pose indices and weights
    """
    psd_count = reader.getPSDCount()
    columns = reader.getPSDColumnIndices()
    rows = reader.getPSDRowIndices()
    values = reader.getPSDValues()

    psd_indices = {}

    # names = get_pose_names(reader)

    for psd, pose, weight in zip(rows, columns, values):
        # if as_names:
        #     pose = names[pose]
        #     psd = names[psd]

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


def get_all_board_controls():
    frm_group = "FRM_faceGUI"
    transforms = cmds.listRelatives(frm_group, type="transform")

    groups = [transform for transform in transforms if transform.startswith("GRP_")]

    controls = []

    for group in groups:
        transforms = cmds.listRelatives(group, allDescendents=True, type="transform")
        controls += [transform for transform in transforms if transform.startswith("CTRL_")]

    return controls


def reset_control_board_anim():
    controls = get_all_board_controls()
    cmds.cutKey(controls, clear=True)

    for control in controls:
        cmds.xform(control, translation=(0,0,0))

    return True

def map_expressions_to_controls(tongue=False, eyelashes=False):
    """Parse expression set driven keys and return dict mapping to driver controls and values
    """
    exp_node = "CTRL_expressions"
    exp_attrs = cmds.listAttr(exp_node, userDefined=True)

    data = [
        # hard coded eye direction
        # these are keyed to LOC_L_eyeDriver
        # so lets just give them here
        ('eyeLookDownL', ('CTRL_L_eye.translateY', -1.0)),
        ('eyeLookDownR', ('CTRL_R_eye.translateY', -1.0)),
        ('eyeLookLeftL', ('CTRL_L_eye.translateX', 1.0)),
        ('eyeLookLeftR', ('CTRL_R_eye.translateX', 1.0)),
        ('eyeLookRightL', ('CTRL_L_eye.translateX', -1.0)),
        ('eyeLookRightR', ('CTRL_R_eye.translateX', -1.0)),
        ('eyeLookUpL', ('CTRL_L_eye.translateY', 1.0)),
        ('eyeLookUpR', ('CTRL_R_eye.translateY', 1.0)),
    ]

    for exp_attr in exp_attrs:
        anim_nodes = cmds.listConnections(
            "{}.{}".format(exp_node, exp_attr), source=True, destination=False, type="animCurve"
        )

        if "eyeLook" in exp_attr:
            continue

        if "eyelashes" in exp_attr and not eyelashes:
            continue

        if "tongue" in exp_attr and not tongue:
            continue

        if not anim_nodes:
            # data[exp_attr] = None
            continue

        driver_attr = cmds.listConnections(
            "{}.input".format(anim_nodes[0]),
            source=True,
            destination=False,
            skipConversionNodes=True,
            plugs=True,
        )[0]

        exp_values = cmds.keyframe(anim_nodes[0], query=True, valueChange=True)
        ctl_values = cmds.keyframe(anim_nodes[0], query=True, floatChange=True)

        # debug
        debug_msg = "{} - {} - {}\n".format(exp_attr, anim_nodes[0], driver_attr)

        for exp_value, ctl_value in zip(exp_values, ctl_values):
            debug_msg += "    {} - {}\n".format(ctl_value, exp_value)

        LOG.info(debug_msg)

        # check values
        if len(exp_values) != 2 and len(ctl_values) != 2:
            LOG.warning("Cannot map exp: {}".format(exp_attr))
            # data[exp_attr] = None
            continue

        if exp_values[0] == 1.0:
            driver_value = ctl_values[0]
        elif exp_values[1] == 1.0:
            driver_value = ctl_values[1]
        else:
            LOG.warning("Cannot map exp: {}".format(exp_attr))
            # data[exp_attr] = None
            continue

        # add data
        # data[exp_attr] = (driver_attr, driver_value)
        data.append((exp_attr, (driver_attr, driver_value)))

    return data


def map_psds_to_controls(expression_mapping, psd_poses):

    expression_mapping = {data[0]: data[1] for data in expression_mapping}

    print("TEST", expression_mapping)

    psd_mapping = []

    for psd_pose in psd_poses:
        poses = psd_pose.get_all_input_poses()

        drivers = []

        for pose in poses:
            if pose.name not in expression_mapping:
                LOG.warning("input pose not mapped: {}".format(pose.name))
                continue

            drivers.append(expression_mapping[pose.name])

        psd_mapping.append((psd_pose.pose.name, drivers))

    return psd_mapping


def animate_attr(attr, value, frame, interval):
    node, attr = attr.split(".")

    LOG.info("    {}.{} {}".format(node, attr, value))

    cmds.setKeyframe(
        node, at=attr, t=frame, value=0, outTangentType="linear", inTangentType="linear",
    )

    frame += interval

    cmds.setKeyframe(
        node, at=attr, t=frame, value=value, outTangentType="linear", inTangentType="linear",
    )

    frame += interval

    cmds.setKeyframe(
        node, at=attr, t=frame, value=0, outTangentType="linear", inTangentType="linear",
    )

    return frame


def animate_ctrl_rom(
        start_frame=0,
        tongue=False,
        eyelashes=False,
        interval=5,
        combos=True,
        dna_file=None,
        combo_mapping=None,
        update_timeline=True,
        combine_lr=False,
        annotate=True,
):

    # TODO combine lr

    mapping = map_expressions_to_controls(tongue=tongue, eyelashes=eyelashes)

    if combos:
        if combo_mapping:
            mapping.update(combo_mapping)
        elif dna_file:
            LOG.info("Loading dna: {}".format(dna_file))
            dna_obj = dna_viewer.DNA(dna_file)
            reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

            poses = get_all_poses(reader)
            psd_poses = get_psd_poses(reader, poses)

            combo_mapping = map_psds_to_controls(mapping, psd_poses.values())
            # mapping.update(combo_mapping)
            mapping += combo_mapping
        else:
            raise mhCore.MHError("either dna file or combo_mapping must be specified")

    # organise combos
    combo_groups = [
        ("CTRL_L_brow_down.translateY", 1.0),
        ("CTRL_R_brow_down.translateY", 1.0),
        ("CTRL_C_jaw.translateY", 1.0),
        ("CTRL_C_jaw.translateX", 1.0),
        ("CTRL_C_jaw.translateX", -1.0),
        ("CTRL_L_eye_blink.translateY", 1.0),
        ("CTRL_R_eye_blink.translateY", 1.0),
        ("CTRL_L_mouth_cornerPull.translateY", 1.0),
        ("CTRL_R_mouth_cornerPull.translateY", 1.0),
        ("CTRL_L_mouth_stretch.translateY", 1.0),
        ("CTRL_R_mouth_stretch.translateY", 1.0),
        ("CTRL_L_mouth_upperLipRaise.translateY", 1.0),
        ("CTRL_R_mouth_upperLipRaise.translateY", 1.0),
        ("CTRL_L_mouth_dimple.translateY", 1.0),
        ("CTRL_R_mouth_dimple.translateY", 1.0),
    ]

    combo_groups_dict = {a: b for a, b in combo_groups}

    ungrouped_mapping = []
    grouped_mapping = {}

    for exp_attr, data in mapping:
        if isinstance(data, list):
            group = None

            # check if this combo contains a control value that's in combo grouping
            attrs = [attr for attr, value in data]

            for combo_attr, combo_value in combo_groups:
                if combo_attr in attrs:
                    group = combo_attr
                    break

            if group:
                if group in grouped_mapping:
                    grouped_mapping[group].append((exp_attr, data))
                else:
                    grouped_mapping[group] = [(exp_attr, data)]
            else:
                ungrouped_mapping.append((exp_attr, data))
        else:
            ungrouped_mapping.append((exp_attr, data))

    LOG.info("Grouped mappings:")

    for group, data in grouped_mapping.items():
        LOG.info("  {}".format(group))

        for attr, value in data:
            LOG.info("    {}: {}".format(attr, value))

    # create animation
    frame = start_frame

    LOG.info("Animating controls...")

    left_frames = {}
    annotation_data = []

    for exp_attr, data in ungrouped_mapping:
        LOG.info("Keying: {}".format(exp_attr))

        exp_frame = frame

        if combine_lr:
            if exp_attr.endswith("R"):
                l_exp_attr = exp_attr[:-1]+"L"
                if l_exp_attr in left_frames:
                    exp_frame = left_frames[l_exp_attr]

            elif exp_attr.endswith("L"):
                left_frames[exp_attr] = exp_frame

        # TODO check keyable
        if isinstance(data, list):
            annotation_text = ""

            for attr, value in data:
                next_frame = animate_attr(attr, value, exp_frame, interval)

                # TODO continue annotation
                annotation_text += ""

        else:
            attr, value = data
            next_frame = animate_attr(attr, value, exp_frame, interval)

        if not (combine_lr and exp_attr.endswith("R")):
            frame = next_frame

    LOG.info("Animating groups...")

    left_group_frames = {}

    for combo_ctrl_attr, combo_value in combo_groups:
        if combine_lr:
            if combo_ctrl_attr.startswith("CTRL_L_"):
                left_group_frames[combo_ctrl_attr] = frame
            elif combo_ctrl_attr.startswith("CTRL_R_"):
                continue

        combo_data = grouped_mapping[combo_ctrl_attr]
        combo_ctrl, combo_attr = combo_ctrl_attr.split(".")

        LOG.info("group: {} {}".format(combo_attr, combo_value))

        # animate primary combo attr
        cmds.setKeyframe(
            combo_ctrl, at=combo_attr, t=frame, value=0, outTangentType="linear", inTangentType="linear",
        )

        frame += interval

        cmds.setKeyframe(
            combo_ctrl, at=combo_attr, t=frame, value=combo_value, outTangentType="linear", inTangentType="linear",
        )

        frame += interval

        # animate combos
        next_frame = frame

        for exp_attr, pose_data in combo_data:
            if combine_lr and exp_attr.endswith("L"):
                left_frames[exp_attr] = frame

            for attr, value in pose_data:
                if attr == combo_ctrl_attr:
                    continue

                next_frame = animate_attr(attr, value, frame, interval)

            frame = next_frame

        # reset primary combo attr
        cmds.setKeyframe(
            combo_ctrl, at=combo_attr, t=frame, value=combo_value, outTangentType="linear", inTangentType="linear",
        )

        frame += interval

        cmds.setKeyframe(
            combo_ctrl, at=combo_attr, t=frame, value=0, outTangentType="linear", inTangentType="linear",
        )

    # animate right groups
    if combine_lr:
        for l_combo_ctrl_attr, l_frame in left_group_frames.items():
            r_combo_ctrl_attr = l_combo_ctrl_attr.replace("_L_", "_R_")

            combo_value = combo_groups_dict[r_combo_ctrl_attr]
            combo_data = grouped_mapping[r_combo_ctrl_attr]
            combo_ctrl, combo_attr = r_combo_ctrl_attr.split(".")

            LOG.info("group: {} {}".format(combo_attr, combo_value))

            # animate primary combo attr
            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=l_frame, value=0, outTangentType="linear", inTangentType="linear",
            )

            l_frame += interval

            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=l_frame, value=combo_value, outTangentType="linear", inTangentType="linear",
            )

            l_frame += interval

            # animate combos
            # assumes combo data is in same order as left combo data
            next_frame = l_frame

            for exp_attr, pose_data in combo_data:
                for attr, value in pose_data:
                    if attr == r_combo_ctrl_attr:
                        continue

                    next_frame = animate_attr(attr, value, l_frame, interval)

                l_frame = next_frame

            # reset primary combo attr
            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=l_frame, value=combo_value, outTangentType="linear", inTangentType="linear",
            )

            l_frame += interval

            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=l_frame, value=0, outTangentType="linear", inTangentType="linear",
            )


    if update_timeline:
        cmds.playbackOptions(animationStartTime=start_frame)
        cmds.playbackOptions(minTime=start_frame)

        cmds.playbackOptions(animationEndTime=frame)
        cmds.playbackOptions(maxTime=frame)

    LOG.info("ROM complete")

    return True
