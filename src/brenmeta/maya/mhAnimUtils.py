import json
from maya import cmds

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils

LOG = mhCore.get_basic_logger(__name__)

ANNOTATION_NAME = "MH_annotation"

COMBO_GROUPS = [
            ("browDownL", "CTRL_L_brow_down.translateY", 1.0),
            ("browDownR", "CTRL_R_brow_down.translateY", 1.0),
            ("jawOpen", "CTRL_C_jaw.translateY", 1.0),
            ("jawLeft", "CTRL_C_jaw.translateX", -1.0),
            ("jawRight", "CTRL_C_jaw.translateX", 1.0),
            ("eyeBlinkL", "CTRL_L_eye_blink.translateY", 1.0),
            ("eyeBlinkR", "CTRL_R_eye_blink.translateY", 1.0),
            ("mouthCornerPullL", "CTRL_L_mouth_cornerPull.translateY", 1.0),
            ("mouthCornerPullR", "CTRL_R_mouth_cornerPull.translateY", 1.0),
            ("mouthStretchL", "CTRL_L_mouth_stretch.translateY", 1.0),
            ("mouthStretchR", "CTRL_R_mouth_stretch.translateY", 1.0),
            ("mouthUpperLipRaiseL", "CTRL_L_mouth_upperLipRaise.translateY", 1.0),
            ("mouthUpperLipRaiseR", "CTRL_R_mouth_upperLipRaise.translateY", 1.0),
            ("mouthDimpleL", "CTRL_L_mouth_dimple.translateY", 1.0),
            ("mouthDimpleR", "CTRL_R_mouth_dimple.translateY", 1.0),
        ]


def create_type_text(name, text):
    type_node = cmds.createNode("type", name="{}_type".format(name))
    transform = cmds.createNode("transform", name=name)
    shape = cmds.createNode("mesh", name="{}Shape".format(name), parent=transform)

    cmds.connectAttr(
        "{}.outputMesh".format(type_node),
        "{}.inMesh".format(shape)
    )

    if text:
        text_hex = ' '.join(f'{b:02X}' for b in text.encode('utf-8'))

        cmds.setAttr(
            "{}.textInput".format(type_node), text_hex, type="string"
        )
    else:
        cmds.setAttr(
            "{}.textInput".format(type_node), "", type="string"
        )

    return type_node, transform, shape


def set_animated_text(type_node, text_data):
    """Set animated text on a type node

    text_data must be formated as a list of tuples: (<text>, <frame>)

    eg.
    data = {
        0: "stuff",
        10: "things",
        30: "test",
    }

    """

    cmds.setAttr("{}.generator".format(type_node), 8)

    data = [
        {
            "hex": ' '.join(f'{b:02X}' for b in text_data[frame].encode('utf-8')),
            "frame": frame,
        } for frame in sorted(text_data.keys())
    ]

    str_data = json.dumps(data)

    cmds.setAttr("{}.animatedType".format(type_node), str_data, type="string")

    return True


def get_all_board_controls(namespace=None):
    frm_group = "FRM_faceGUI"
    grp_prefix = "GRP_"
    ctrl_prefix = "CTRL_"

    if namespace:
        frm_group = "{}:{}".format(namespace, frm_group)
        grp_prefix = "{}:{}".format(namespace, grp_prefix)
        ctrl_prefix = "{}:{}".format(namespace, ctrl_prefix)

    transforms = cmds.listRelatives(frm_group, type="transform")

    groups = [transform for transform in transforms if transform.startswith(grp_prefix)]

    controls = []

    for group in groups:
        transforms = cmds.listRelatives(group, allDescendents=True, type="transform")
        controls += [transform for transform in transforms if transform.startswith(ctrl_prefix)]

    return controls


def connect_control_boards(src_namespace=None, dst_namespace=None):
    if src_namespace == dst_namespace == None:
        raise mhCore.MHError("src and dst namespaces cannot both be None")

    src_controls = get_all_board_controls(namespace=src_namespace)

    for src_control in src_controls:
        if src_namespace:
            control_name = src_control.split(":")[1]
        else:
            control_name = src_control

        if dst_namespace:
            dst_control = "{}:{}".format(dst_namespace, control_name)
        else:
            dst_control = control_name

        cmds.connectAttr(
            "{}.translate".format(src_control),
            "{}.translate".format(dst_control),
        )

    return True


def reset_control_board_anim(namespace=None):
    controls = get_all_board_controls(namespace=namespace)
    cmds.cutKey(controls, clear=True)

    for control in controls:
        cmds.xform(control, translation=(0,0,0))

    return True

def map_expressions_to_controls(tongue=False, eyelashes=False, head_turn=False, namespace=None):
    """Parse expression set driven keys and return dict mapping to driver controls and values
    """
    exp_node = "CTRL_expressions"

    if namespace:
        exp_node = "{}:{}".format(namespace, exp_node)

    exp_attrs = sorted(cmds.listAttr(exp_node, userDefined=True))

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

    if namespace:
        data = [(name, ("{}:{}".format(namespace, attr), value)) for name, (attr, value) in data]

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

        if ("turn" in exp_attr or "tilt" in exp_attr) and not head_turn:
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
            continue

        if exp_values[0] == 1.0:
            driver_value = ctl_values[0]
        elif exp_values[1] == 1.0:
            driver_value = ctl_values[1]
        else:
            LOG.warning("Cannot map exp: {}".format(exp_attr))
            continue

        # add data
        data.append((exp_attr, (driver_attr, driver_value)))

    return data


def map_psds_to_controls(expression_mapping, psd_poses):

    expression_mapping = {data[0]: data[1] for data in expression_mapping}

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


def group_mapped_combos(mapping, combo_groups, namespace=None, debug=True):
    """Group combos that have been mapped to control attributes by if they contain one of the attributes in combo_groups

    Prioritised by attr order defined by combo_groups

    eg.
    COMBO_GROUPS = [
            ("browDownL", "CTRL_L_brow_down.translateY", 1.0),
            ("browDownR", "CTRL_R_brow_down.translateY", 1.0),
            ("jawOpen", "CTRL_C_jaw.translateY", 1.0),
            ("jawLeft", "CTRL_C_jaw.translateX", 1.0),
            ....

    """

    ungrouped_mapping = []
    grouped_mapping = {}

    for exp_attr, data in mapping:
        if isinstance(data, list):
            group = None

            # check if this combo contains a control value that's in combo grouping
            attr_values = {attr: value for attr, value in data}

            for shape, combo_attr, combo_value in combo_groups:
                if combo_attr in attr_values:
                    if attr_values[combo_attr] == combo_value:
                        group = shape
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

    return grouped_mapping, ungrouped_mapping


def group_additional_combos(grouped_mapping, ungrouped_mapping):
    amended_ungrouped_mapping = []

    for exp_attr, data in ungrouped_mapping:
        # skip combos
        if isinstance(data, list):
            continue

        attr, value = data

        if "tongue" in attr:
            grouped_mapping["jawOpen"].append((exp_attr, [data]))
        else:
            amended_ungrouped_mapping.append((exp_attr, data))

    return grouped_mapping, amended_ungrouped_mapping


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
        combo_mapping=None,
        update_timeline=True,
        combine_lr=False,
        annotate=True,
        namespace=None,
        combo_groups=COMBO_GROUPS,
        debug=True,
):

    mapping = map_expressions_to_controls(
        tongue=True,
        eyelashes=eyelashes,
        namespace=namespace
    )

    if combos:
        if combo_mapping:
            mapping += combo_mapping
        else:
            raise mhCore.MHError("combo_mapping must be specified")

    # organise combos
    if namespace:
        combo_groups = [
            ("{}:{}".format(namespace, attr), value)
            for attr, value in combo_groups
        ]

    grouped_mapping, ungrouped_mapping = group_mapped_combos(
        mapping, combo_groups, namespace=namespace, debug=True
    )

    grouped_mapping, ungrouped_mapping = group_additional_combos(grouped_mapping, ungrouped_mapping)

    if debug:
        # log grouping for debugging
        LOG.info("Grouped mappings:")

        for group, data in grouped_mapping.items():
            LOG.info("  {}".format(group))

            for exp_attr, data in data:
                LOG.info("    {}: {}".format(exp_attr, data))

    # create animation
    frame = start_frame

    LOG.info("Animating controls...")

    left_frames = {}
    annotation_data = {}

    for exp_attr, data in ungrouped_mapping:
        if exp_attr is None:
            continue

        LOG.info("Keying: {}".format(exp_attr))

        exp_frame = frame

        if combine_lr:
            # either store the exp frame for later if this is a left expression
            # or retrieve the left frame if it's a right expression
            if exp_attr.endswith("R"):
                l_exp_attr = exp_attr[:-1]+"L"
                if l_exp_attr in left_frames:
                    exp_frame = left_frames[l_exp_attr]

            elif exp_attr.endswith("L"):
                left_frames[exp_attr] = exp_frame

        # append annotation
        if exp_frame not in annotation_data:
            annotation_data[exp_frame] = ""

        annotation_data[exp_frame] += "{}\n".format(exp_attr)

        # create keyframes and append annotation
        # TODO check keyable
        if isinstance(data, list):
            for attr, value in data:
                next_frame = animate_attr(attr, value, exp_frame, interval)
                annotation_data[exp_frame] += "    {}\n".format(attr)
        else:
            attr, value = data
            next_frame = animate_attr(attr, value, exp_frame, interval)
            annotation_data[exp_frame] += "    {}\n".format(attr)

        # continue to next expression
        if not (combine_lr and exp_attr.endswith("R")):
            frame = next_frame

        annotation_data[exp_frame] += "\n\n"

    # animate middle and left combo groups
    if combos:
        LOG.info("Animating groups...")

        left_group_frames = {}

        for group, combo_ctrl_attr, combo_value in combo_groups:
            if combine_lr:
                if "_L_" in combo_ctrl_attr:
                    left_group_frames[group] = [frame]
                elif "_R_" in combo_ctrl_attr:
                    continue

            combo_data = grouped_mapping[group]
            combo_ctrl, combo_attr = combo_ctrl_attr.split(".")

            LOG.info("group: {} {} {}".format(group, combo_ctrl_attr, combo_value))

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
                if exp_attr is None:
                    continue

                LOG.info("Keying: {}".format(exp_attr))

                exp_frame = frame

                # either store the exp frame for later if this is a left expression
                # or retrieve the left frame if it's a right expression
                # note that this is for middle combo_ctrl_attrs
                # that have both left and right grouped expressions
                if combine_lr:
                    if exp_attr.endswith("R"):
                        l_exp_attr = exp_attr[:-1]+"L"
                        if l_exp_attr in left_frames:
                            exp_frame = left_frames[l_exp_attr]

                    elif exp_attr.endswith("L"):
                        left_frames[exp_attr] = exp_frame

                if exp_frame not in annotation_data:
                    annotation_data[exp_frame] = ""

                annotation_data[exp_frame] += "{}\n".format(exp_attr)

                for attr, value in pose_data:
                    annotation_data[exp_frame] += "    {}\n".format(attr)

                    # safeguard to ensure combo control doesn't get keyed during group
                    if attr == combo_ctrl_attr:
                        continue

                    # safeguard to ensure opposite control doesn't get keyed if we're combining l/r combo groups
                    if combine_lr and "_R_" in attr:
                        r_group = combo_ctrl_attr.replace("_L_", "_R_")
                        if attr == r_group:
                            continue

                    # animate attr
                    next_frame = animate_attr(attr, value, exp_frame, interval)

                if not (combine_lr and exp_attr.endswith("R")):
                    frame = next_frame

                annotation_data[exp_frame] += "\n\n"

            # reset primary combo attr
            if combine_lr and "_L_" in combo_ctrl_attr:
                left_group_frames[group].append(frame)

            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=frame, value=combo_value, outTangentType="linear", inTangentType="linear",
            )

            frame += interval

            cmds.setKeyframe(
                combo_ctrl, at=combo_attr, t=frame, value=0, outTangentType="linear", inTangentType="linear",
            )

        # animate right groups
        if combine_lr:
            combo_groups_dict = {group: (ctl_attr, ctl_value) for group, ctl_attr, ctl_value in combo_groups}

            for l_group, (l_frame, l_end_frame) in left_group_frames.items():
                r_group = l_group[:-1] + "R"

                r_combo_ctrl_attr, r_combo_value = combo_groups_dict[r_group]
                r_combo_data = grouped_mapping[r_group]
                r_combo_ctrl, r_combo_attr = r_combo_ctrl_attr.split(".")

                LOG.info("group: {} {}".format(r_group, r_combo_value))

                # animate primary combo attr
                cmds.setKeyframe(
                    r_combo_ctrl, at=r_combo_attr, t=l_frame, value=0, outTangentType="linear", inTangentType="linear",
                )

                l_frame += interval

                cmds.setKeyframe(
                    r_combo_ctrl, at=r_combo_attr, t=l_frame, value=r_combo_value, outTangentType="linear", inTangentType="linear",
                )

                l_frame += interval

                # animate combos
                for exp_attr, pose_data in r_combo_data:
                    if exp_attr is None:
                        continue

                    if not exp_attr.endswith("R"):
                        LOG.warning("non-R expression in R combo: {}".format(exp_attr))
                        continue

                    l_exp_attr = exp_attr[:-1] + "L"

                    if l_exp_attr not in left_frames:
                        LOG.warning("left expression not found: {}".format(l_exp_attr))
                        continue

                    exp_frame = left_frames[l_exp_attr]

                    annotation_data[exp_frame] += "{}\n".format(exp_attr)

                    for attr, value in pose_data:
                        annotation_data[exp_frame] += "    {}\n".format(attr)

                        # safeguard to ensure neither l or r combo controls get keyed during group
                        if attr in [r_group, l_group]:
                            continue

                        # animate attr
                        next_frame = animate_attr(attr, value, exp_frame, interval)

                # reset primary combo attr
                cmds.setKeyframe(
                    r_combo_ctrl, at=r_combo_attr, t=l_end_frame, value=r_combo_value, outTangentType="linear", inTangentType="linear",
                )

                cmds.setKeyframe(
                    r_combo_ctrl, at=r_combo_attr, t=l_end_frame + interval, value=0, outTangentType="linear", inTangentType="linear",
                )


    if update_timeline:
        cmds.playbackOptions(animationStartTime=start_frame)
        cmds.playbackOptions(minTime=start_frame)

        cmds.playbackOptions(animationEndTime=frame)
        cmds.playbackOptions(maxTime=frame)

    if annotate:
        type_node, transform, shape = create_type_text(ANNOTATION_NAME, None)
        set_animated_text(type_node, annotation_data)

    LOG.info("ROM complete")

    return True
