"""utilities to prepare the rig for export to UE
"""

from maya import cmds


def add_root_and_spine():
    """Add body joints
    """
    spine_4 = "spine_04"

    pos = cmds.xform(spine_4, query=True, translation=True, worldSpace=True)
    pos_y = pos[1]

    parent = None

    joint_pos_y = 0

    for joint in [
        "root",
        "pelvis",
        "spine_01",
        "spine_02",
        "spine_03",
    ]:
        cmds.createNode("joint", name=joint, parent=parent)
        cmds.xform(joint, translation=(0, joint_pos_y, 0), worldSpace=True)
        joint_pos_y += pos_y / 5
        parent = joint

    cmds.parent(spine_4, "spine_03")

    return True


def add_ctrl_exp_pose_attrs():
    """Adds CTRL_expressions attrs for all pose attrs found on facial root joint
    Required for UE rigLogic
    """

    root = "FACIAL_C_FacialRoot"
    attrs = cmds.listAttr(root, userDefined=True)

    attrs = [
        i for i in attrs if not any([
            "_color_head_" in i,
            "_normal_head_" in i,
        ])
    ]

    for attr in attrs:
        cmds.addAttr(
            root,
            longName="CTRL_expressions_{}".format(attr),
            min=0.0,
            max=1.0,
            keyable=True,
        )

    return True


def key_pose_attrs():
    """
    Unreal needs an attr to be keyed to bring it in as an anim curve,
    and it needs at least two keyframes (on anything) to consider it animation
    """
    root = "FACIAL_C_FacialRoot"
    attrs = cmds.listAttr(root, userDefined=True)

    cmds.setKeyframe(
        "{}.t".format(root), t=0
    )

    cmds.setKeyframe(
        "{}.t".format(root), t=10
    )

    for attr in attrs:
        cmds.setKeyframe(
            "{}.{}".format(root, attr), t=0
        )

    return True


def create_materials():
    for mesh in cmds.listRelatives("head_lod0_grp"):

        name = mesh.split("_")[0]

        shading_node = cmds.shadingNode("lambert", name="{}_material".format(name), asShader=True)

        set_node = cmds.sets(
            name="{}_shadingGroup".format(name), renderable=True, noSurfaceShader=True, empty=True
        )

        cmds.connectAttr(
            "{}.outColor".format(shading_node),
            "{}.surfaceShader".format(set_node)
        )

        cmds.sets(mesh, edit=True, forceElement=set_node)

    return True
