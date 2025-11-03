import random

from maya import cmds

from . import mhMayaUtils
from . import mhJoints

SNAP = [
    "FACIAL_L_EyeCornerOuter1",
    "FACIAL_R_EyeCornerOuter1",
    "FACIAL_C_NoseLower",
    "FACIAL_L_Ear",
    "FACIAL_R_Ear",
    # eyelid offsets
    "FACIAL_L_EyelidUpperA1",
    "FACIAL_L_EyelidUpperA2",
    "FACIAL_L_EyelidUpperA3",
    "FACIAL_R_EyelidUpperA1",
    "FACIAL_R_EyelidUpperA2",
    "FACIAL_R_EyelidUpperA3",
]

EXCLUDE = [
    "FACIAL_L_Pupil",
    "FACIAL_R_Pupil",
    'FACIAL_C_Skull',
    'FACIAL_C_Chin',
    'FACIAL_C_TeethUpper',
    'FACIAL_C_TongueUpper1',
    'FACIAL_L_TongueSide1',
    'FACIAL_R_TongueSide1',
    'FACIAL_C_TongueUpper2',
    'FACIAL_L_TongueSide2',
    'FACIAL_R_TongueSide2',
    'FACIAL_C_TongueUpper3',
    'FACIAL_C_TongueLower3',
    'FACIAL_L_TongueSide3',
    'FACIAL_R_TongueSide3',
    'FACIAL_L_TongueSide4',
    'FACIAL_R_TongueSide4',
]

DEFAULT_OFFSET_VECTOR = (0, 0, 1)

AVERAGE_CHILDREN_PLUS_OFFSET = [
    # brows
    "FACIAL_R_ForeheadOut",
    "FACIAL_R_ForeheadMid",
    "FACIAL_R_ForeheadIn",
    "FACIAL_C_Forehead",
    "FACIAL_L_ForeheadIn",
    "FACIAL_L_ForeheadMid",
    "FACIAL_L_ForeheadOut",
    # eye sack
    "FACIAL_L_EyesackUpper",
    "FACIAL_L_EyesackLower",
    "FACIAL_R_EyesackUpper",
    "FACIAL_R_EyesackLower",
    # cheeks
    "FACIAL_L_CheekInner",
    "FACIAL_L_CheekOuter",
    "FACIAL_L_CheekLower",
    "FACIAL_R_CheekInner",
    "FACIAL_R_CheekOuter",
    "FACIAL_R_CheekLower",
    # TODO check the results for these ones
    "FACIAL_L_NasolabialBulge",
    "FACIAL_R_NasolabialBulge",
    ("FACIAL_L_Jawline", (1, 0, 0)),
    ("FACIAL_R_Jawline", (-1, 0, 0)),
    # eyelid furrow gives issues with this method
    # "FACIAL_L_EyelidUpperFurrow",
    # "FACIAL_R_EyelidUpperFurrow",
]

AVERAGE_CHILDREN = [
    # eyelids
    "FACIAL_L_EyelidUpperFurrow",
    "FACIAL_R_EyelidUpperFurrow",
    # nose
    "FACIAL_L_Nostril",
    "FACIAL_R_Nostril",
    # lips
    "FACIAL_C_LipUpper",
    "FACIAL_L_LipUpper",
    "FACIAL_L_LipUpperOuter",
    "FACIAL_R_LipUpper",
    "FACIAL_R_LipUpperOuter",
    "FACIAL_L_LipCorner",
    "FACIAL_L_LipLowerOuter",
    "FACIAL_L_LipLower",
    "FACIAL_C_LipLower",
    "FACIAL_R_LipLower",
    "FACIAL_R_LipLowerOuter",
    "FACIAL_R_LipCorner",
    # neck
    "FACIAL_C_Neck2Root",
    "FACIAL_C_Neck1Root",
]

PROJECT_AXES = [
    # joint, aim, up, furthest
    # TODO this is generally not working, change to child average
    ("FACIAL_L_EyeCornerOuter", (1, 0, 0), (0, 1, 0), False),
    ("FACIAL_L_EyeCornerInner", (-1, 0, 0), (0, 1, 0), False),
    ("FACIAL_R_EyeCornerOuter", (-1, 0, 0), (0, 1, 0), False),
    ("FACIAL_R_EyeCornerInner", (1, 0, 0), (0, 1, 0), False),
    # nose
    ("FACIAL_C_Nose", (0, 0, 1), (1, 0, 0), True),
    ("FACIAL_C_NoseTip", (0, 0, 1), (1, 0, 0), True),
    # mouth
    ("FACIAL_C_MouthUpper", (0, 0, 1), (1, 0, 0), True),
    ("FACIAL_C_MouthLower", (0, 0, 1), (1, 0, 0), True),
    ("FACIAL_C_LowerLipRotation", (0, 0, 1), (1, 0, 0), True),
    ("FACIAL_C_Jaw", (0, 0, 1), (1, 0, 0), True),
    ("FACIAL_C_Chin", (0, 0, 1), (1, 0, 0), True),
    # head/neck
    # TODO maybe some correction to clean up orientation
    ("head", (0, 1, 0), (0, 0, 1), True),
    ("neck_02", (0, 1, 0), (0, 0, 1), True),
    ("neck_01", (0, 1, 0), (0, 0, 1), True),
    ("FACIAL_C_FacialRoot", (0, 1, 0), (0, 0, 1), True),
    ("FACIAL_C_Skull", (0, 1, 0), (1, 0, 0), True),
]


def set_joint_look(default_visibility=True):
    # set draw styles
    bone = 0
    box = 1  # multi-child as box
    none = 2
    joint = 3

    for joint_name, draw_style in [
        ("FACIAL_C_FacialRoot", joint),
        ("FACIAL_C_LowerLipRotation", joint),
        ("FACIAL_C_Jaw", joint),
        ("FACIAL_C_MouthUpper", joint),
        ("FACIAL_C_MouthLower", joint),
        ("FACIAL_C_Neck2Root", joint),
        ("FACIAL_C_Neck1Root", joint),
        ("FACIAL_L_Ear", joint),
        ("FACIAL_R_Ear", joint),
    ]:
        cmds.setAttr(
            "{}.drawStyle".format(joint_name), draw_style
        )

    # create vis layers
    random.seed(13)

    for name in [
        ("Sideburn", ["*Masseter", "*JawBulge", "*JawRecess"]),
        "Ear",
        "Hair",
        "Neck",
        "Cheek",
        "Forehead",
        "Chin",
        "MouthUpper",
        "MouthLower",
        "Teeth",
        "Jawline",
        "Nasolabial",
        "Nose",
        "Eye",
        "Skin",
        "MouthInterior",
        "Temple",
        "clavicle",
    ]:
        if isinstance(name, tuple):
            name, ls = name
        else:
            ls = []

        ls.append("*{}*".format(name))

        joints = cmds.ls(ls, type="joint")

        layer_name = "{}_layer".format(name)

        if cmds.objExists(layer_name):
            cmds.delete(layer_name)

        cmds.createDisplayLayer(joints, name=layer_name)

        cmds.setAttr("{}.overrideRGBColors".format(layer_name), True)

        cmds.setAttr(
            "{}.overrideColorRGB".format(layer_name),
            random.uniform(0, 1.0), random.uniform(0, 1.0), random.uniform(0, 1.0)
        )

        cmds.setAttr("{}.visibility".format(layer_name), default_visibility)


    # set colours
    red = (1, 0, 0)
    green = (0, 1, 0)
    blue = (0, 0, 1)

    dark_red = (0.5, 0, 0)
    dark_green = (0, 0.5, 0)
    dark_blue = (0, 0, 0.5)

    yellow = (1, 1, 0)
    light_blue = (0, 1, 1)
    violet = (1, 0, 1)

    pastel_green = (0.2, 1.0, 0.0)
    pastel_orange = (1.0, 0.2, 0.0)
    pastel_yellow = (1.0, 0.7, 0.0)
    pastel_blue = (0, 0.2, 1.0)
    sky_blue = (0, 0.7, 1.0)
    pink = (1.0, 0.2, 1.0)

    for joint, colour in [
        # forehead
        ("FACIAL_C_Forehead", pastel_green),
        ("FACIAL_L_ForeheadIn", red),
        ("FACIAL_L_ForeheadMid", pastel_orange),
        ("FACIAL_L_ForeheadOut", pastel_yellow),
        ("FACIAL_R_ForeheadIn", blue),
        ("FACIAL_R_ForeheadMid", pastel_blue),
        ("FACIAL_R_ForeheadOut", sky_blue),
        # nose
        ("FACIAL_C_NoseTip", pastel_green),
        ("FACIAL_C_NoseLower", green),
        ("FACIAL_L_Nostril", red),
        ("FACIAL_R_Nostril", blue),
        # eyes
        ("FACIAL_L_EyelidUpperFurrow", red),
        ("FACIAL_L_EyeParallel", red),
        ("FACIAL_L_EyelidUpperA", pastel_orange),
        ("FACIAL_L_EyelidUpperB", pastel_yellow),
        ("FACIAL_L_EyelidLowerA", pastel_orange),
        ("FACIAL_L_EyelidLowerB", pastel_yellow),
        ("FACIAL_R_EyelidUpperFurrow", blue),
        ("FACIAL_R_EyeParallel", blue),
        ("FACIAL_R_EyelidUpperA", pastel_blue),
        ("FACIAL_R_EyelidUpperB", sky_blue),
        ("FACIAL_R_EyelidLowerA", pastel_blue),
        ("FACIAL_R_EyelidLowerB", sky_blue),
        # lip upper
        ("FACIAL_C_LipUpper", green),
        ("FACIAL_L_LipUpper", red),
        ("FACIAL_L_LipUpperOuter", pastel_orange),
        ("FACIAL_L_LipCorner", yellow),
        ("FACIAL_R_LipUpper", blue),
        ("FACIAL_R_LipUpperOuter", pastel_blue),
        ("FACIAL_R_LipCorner", light_blue),
        ("FACIAL_C_LipLower", pastel_green),
        ("FACIAL_L_LipLower", violet),
        ("FACIAL_L_LipLowerOuter", pink),
        ("FACIAL_R_LipLower", violet),
        ("FACIAL_R_LipLowerOuter", pink),
        # cheeks
        ("FACIAL_L_EyesackLower", dark_red),
        ("FACIAL_L_EyesackUpper", dark_red),
        ("FACIAL_L_CheekInner", dark_red),
        ("FACIAL_L_CheekOuter", dark_red),
        ("FACIAL_L_NasolabialBulge", dark_red),
        ("FACIAL_L_CheekLower", dark_red),
        ("FACIAL_L_Jawline", dark_red),
        ("FACIAL_R_EyesackLower", dark_blue),
        ("FACIAL_R_EyesackUpper", dark_blue),
        ("FACIAL_R_CheekInner", dark_blue),
        ("FACIAL_R_CheekOuter", dark_blue),
        ("FACIAL_R_NasolabialBulge", dark_blue),
        ("FACIAL_R_CheekLower", dark_blue),
        ("FACIAL_R_Jawline", dark_blue),
        # inner mouth
        ("FACIAL_C_TeethLower", dark_green),
        # neck
        ("FACIAL_C_Neck2Root", dark_green),
        ("FACIAL_C_Neck1Root", pastel_green),
    ]:
        # re-connect layer
        cons = cmds.listConnections("{}.drawOverride".format(joint), plugs=True)

        if cons:
            layer = cons[0].split(".")[0]
            cmds.disconnectAttr(cons[0], "{}.drawOverride".format(joint))
            cmds.connectAttr("{}.visibility".format(layer), "{}.overrideVisibility".format(joint))

        # set overrides
        cmds.setAttr("{}.overrideEnabled".format(joint), True)
        cmds.setAttr("{}.overrideRGBColors".format(joint), True)
        cmds.setAttr("{}.overrideColorRGB".format(joint), *colour)

    return True


def get_neck_spine_offset():
    neck_pos = cmds.xform("neck_01", query=True, translation=True, worldSpace=True)
    spine_pos = cmds.xform("spine_05", query=True, translation=True, worldSpace=True)

    offset = [a - b for a, b in zip(neck_pos, spine_pos)]

    return offset


def restore_neck_spine_offset(orig_neck_pos, root="spine_04"):
    neck_pos = cmds.xform("neck_01", query=True, translation=True, worldSpace=True)

    offset = [a - b for a, b in zip(neck_pos, orig_neck_pos)]

    root_pos = cmds.xform(root, query=True, translation=True, worldSpace=True)
    offset_pos = [a + b for a, b in zip(root_pos, offset)]
    cmds.xform(root, translation=offset_pos, worldSpace=True)
    cmds.xform("neck_01", translation=neck_pos, worldSpace=True)

    return True


def transfer_joint_placement(root, src_head, dst_head, threshold=0.5):
    leaf_joints = mhMayaUtils.get_leaf_transforms(root, allDescendents=True)

    snap_joints = leaf_joints + SNAP
    snap_joints = [i for i in snap_joints if i not in EXCLUDE]

    # ** get data **

    # get snap mapping
    snap_mapping = mhJoints.map_joints_to_vertex_ids(
        snap_joints, src_head, threshold=threshold
    )

    unmapped_joints = [i for i in leaf_joints if i not in snap_mapping]
    unmapped_joints = [i for i in unmapped_joints if i not in EXCLUDE]

    if unmapped_joints:
        print("[ WARNING ] Failed to map some leaf joints: {}".format(unmapped_joints))

    # get offsets
    joint_offsets = {}

    for joint in AVERAGE_CHILDREN_PLUS_OFFSET:
        if isinstance(joint, tuple):
            vector = joint[1]
            joint = joint[0]
        else:
            vector = DEFAULT_OFFSET_VECTOR

        joint_offset = mhJoints.get_joint_offset_from_mesh(
            joint, src_head, vector, max_distance=10000, both_directions=False
        )

        joint_offsets[joint] = joint_offset

    # project joint axes
    joint_projections = {}
    failed_joints = []

    for joint, aim_vector, up_vector, furthest in PROJECT_AXES:
        try:
            data = mhJoints.map_joint_axes_to_mesh(
                joint,
                src_head,
                aim_vector,
                up_vector,
                furthest=furthest
            )

            joint_projections[joint] = data
        except mhCore.MHError:
            failed_joints.append(joint)

    # fallback to nearest for any joints that fail to project
    print("Failed to project some joints, falling back to nearest vertex:")

    for joint in failed_joints:
        print("    {}".format(joint))

    snap_mapping.update(
        mhJoints.map_joints_to_vertex_ids(
            failed_joints, src_head, threshold=threshold
        )
    )

    # ** transfer joints placements **

    # snap joints
    mhJoints.snap_joints_to_vertex_ids(dst_head, snap_mapping)

    # average to children
    for joint in AVERAGE_CHILDREN:
        mhJoints.snap_joint_to_child_average(joint)

    # average and offset joints
    for joint in AVERAGE_CHILDREN_PLUS_OFFSET:
        if isinstance(joint, tuple):
            vector = joint[1]
            joint = joint[0]
        else:
            vector = DEFAULT_OFFSET_VECTOR

        mhJoints.snap_joint_to_child_average(joint)

        mhJoints.offset_joint_from_mesh(
            joint, dst_head, joint_offsets[joint]
        )

    # project joints to axes
    for joint, aim_vector, up_vector, furthest in PROJECT_AXES:
        if joint not in joint_projections:
            continue

        mhJoints.snap_joint_to_axes_data(
            joint,
            dst_head,
            joint_projections[joint],
            aim_vector=aim_vector,
            up_vector=up_vector,
        )

    return True


def transfer_teeth(src_mesh, dst_mesh):
    """
    """
    for joint in [
        "FACIAL_C_TeethLower",
        "FACIAL_C_TeethUpper",
    ]:
        data = mhJoints.map_joint_axes_to_mesh(
            joint,
            src_mesh,
            (0, 0, 1),
            (1, 0, 0),
        )

        mhJoints.snap_joint_to_axes_data(
            joint,
            dst_mesh,
            data,
            position_only=True
        )

    tongue_data = []

    for i in range(1, 5):
        joint = "FACIAL_C_Tongue{}".format(i)

        data = mhJoints.map_joint_axes_to_mesh(
            joint,
            src_mesh,
            (0, 1, 0),
            (1, 0, 0),
            furthest=False
        )

        tongue_data.append((joint, data))

    for joint, data in tongue_data:
        mhJoints.snap_joint_to_axes_data(
            joint,
            dst_mesh,
            data,
            aim_vector=(0, 1, 0),
            up_vector=(1, 0, 0),
            preserve_children=False
        )

    return True


def transfer_eye(src_mesh, dst_mesh, side):
    # joints
    eye_joint = "FACIAL_{}_Eye".format(side)

    joints = [
        "FACIAL_{}_EyelidLowerA",
        "FACIAL_{}_EyelidLowerB",
        "FACIAL_{}_EyelidUpperA",
        "FACIAL_{}_EyelidUpperB",
    ]

    # snap to middle of eye mesh
    data = mhJoints.map_joint_axes_to_mesh(
        eye_joint,
        src_mesh,
        (0, 0, 1),
        (1, 0, 0),
        furthest=False
    )

    mhJoints.snap_joint_to_axes_data(
        eye_joint,
        dst_mesh,
        data,
        preserve_children=False,
        position_only=True
    )

    for joint in joints:
        joint = joint.format(side)

        mhJoints.snap_joint_to_axes_data(
            joint,
            dst_mesh,
            data,
            preserve_children=True,
            position_only=True
        )

        # aim at average children
        child_positions = [
            cmds.xform(i, query=True, translation=True, worldSpace=True)
            for i in cmds.listRelatives(joint)
        ]

        mean_child_position = mhMayaUtils.get_average_position(child_positions)

        joint_position = cmds.xform(joint, query=True, translation=True, worldSpace=True)

        aim_position = list(joint_position)
        aim_position[0] += 1.0

        matrix = mhMayaUtils.create_aim_matrix_from_positions(
            joint_position, aim_position, mean_child_position, (1, 0, 0), (0, 0, 1)
        )

        mhMayaUtils.xform_preserve_children(
            joint, matrix=matrix, worldSpace=True
        )

    return True
