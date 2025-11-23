"""
Convert pose system to pure blendshapes
"""
import time

from maya.api import OpenMaya
from maya import cmds
from maya import mel

import dna_viewer
import dnacalib

from brenmeta.core import mhCore
from brenmeta.dna1 import mhBehaviour, mhCore
from brenmeta.maya import mhMayaUtils

from brenmy.utils import bmBlendshapeUtils
from brenmy.deformers import bmBlendshape


LOG = mhCore.get_basic_logger(__name__)

DEFAULT_IN_BETWEENS = {
    "jawOpen": 2,
    "eyeBlinkL": 2,
    "eyeBlinkR": 2,
}

ADDITIONAL_COMBOS = [
    ("jawOpen", "teethFwdD"),
    ("jawOpen", "teethBackD"),
    ("jawOpen", "teethUpD"),
    ("jawOpen", "teethDownD")
    # ("jawOpen", "teethLeftD"),
    # ("jawOpen", "teethRightD"),
]

DEFAULT_JOINTS = [
    "FACIAL_L_Eye",
    "FACIAL_L_EyeParallel",
    "FACIAL_R_Eye",
    "FACIAL_R_EyeParallel",
    "FACIAL_C_Jaw",
    "FACIAL_C_LowerLipRotation",
    "FACIAL_C_TeethUpper",
    "FACIAL_C_TeethLower",
    # tongue
    "FACIAL_C_TeethLower",
    "FACIAL_C_Tongue1",
    "FACIAL_C_Tongue2",
    "FACIAL_C_TongueUpper2",
    "FACIAL_L_TongueSide2",
    "FACIAL_R_TongueSide2",
    "FACIAL_C_Tongue3",
    "FACIAL_C_TongueUpper3",
    "FACIAL_C_TongueLower3",
    "FACIAL_L_TongueSide3",
    "FACIAL_R_TongueSide3",
    "FACIAL_C_Tongue4",
]

KEEP_JOINTS = [
    "FACIAL_C_FacialRoot",
    "head",
    "neck_02",
    "neck_01",
    "spine_05",
    "spine_04",
]


def delete_redundant_joints(keep_joints=KEEP_JOINTS, pose_joints=DEFAULT_JOINTS):
    joints = cmds.ls(type="joint")
    joints = [i for i in joints if i not in keep_joints+pose_joints]
    cmds.delete(joints)


def bake_shapes(
        dna_file,
        name="poseSystem",
        expressions_node="CTRL_expressions",
        in_betweens=DEFAULT_IN_BETWEENS,
        mesh="head_lod0_mesh",
        calculate_psd_deltas=True,
        connect_shapes=True,
        optimise=True,
        pose_joints=DEFAULT_JOINTS,
        keep_joints=KEEP_JOINTS,
        additional_combos=ADDITIONAL_COMBOS,
        detailed_verbose=False
):
    """
from brenmy.mh.presets import bmMhFaceShapeBake

dna_file = r"D:\Dev\3rd_party_repos\MetaHuman-DNA-Calibration\data\dna_files\Taro.dna"

bmMhFaceShapeBake.bake_shapes(
    dna_file,
    mesh="head_lod0_mesh",
    calculate_psd_deltas=True,
    connect_shapes=True,
    optimise=True
)


    :param dna_file:
    :param name:
    :param expressions_node:
    :param in_betweens:
    :param mesh:
    :return:

    """

    mhCore.validate_plugin()

    # load dna data
    LOG.info("Loading dna: {}".format(dna_file))

    dna_obj = dna_viewer.DNA(dna_file)

    LOG.info("Getting reader...")
    calib_reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

    # get pose data
    # TODO check poses correspond to expression attrs
    LOG.info("Getting pose data...")

    poses = mhBehaviour.get_all_poses(calib_reader, absolute=True)
    psd_poses = mhBehaviour.get_psd_poses(calib_reader, poses)

    pose_count = len(poses)

    # create additional combos
    if additional_combos:
        LOG.info("Adding additional combos...")

        pose_dict = {
            pose.name: pose for pose in poses
        }


        joints_attr_defaults = mhBehaviour.get_joint_defaults(calib_reader)

        for i, pose_names in enumerate(additional_combos):
            combo = mhBehaviour.PSDPose()

            combo.pose = mhBehaviour.Pose()
            combo.pose.name = "_".join(pose_names)
            combo.pose.index = pose_count + i
            combo.pose.defaults = joints_attr_defaults

            combo.input_poses = [pose_dict[pose_name] for pose_name in pose_names]
            combo.input_weights = [1.0]*len(pose_names)

            psd_poses[combo.pose.index] = combo
            poses.append(combo.pose)

            if detailed_verbose:
                LOG.info("    {}".format(combo))

    # get joints
    root_joints = ["FACIAL_C_Neck2Root", "FACIAL_C_Neck1Root", "FACIAL_C_FacialRoot"]

    transforms = []

    for root_joint in root_joints:
        transforms += cmds.listRelatives(root_joint, allDescendents=True, type="joint")

    # find rl4 node
    rl4_nodes = cmds.ls(type="embeddedNodeRL4")

    if rl4_nodes:
        # get expressions attributes
        rl4_node = rl4_nodes[0]
        expression_attrs = cmds.listConnections("{}.inputs".format(rl4_node), plugs=True)
        expressions = [i.split(".")[1] for i in expression_attrs]
    else:
        rl4_node = None
        expressions = None

    # create expression mapping
    expression_mapping = {
        pose.name: "{}.{}".format(expressions_node, expression)
        for pose, expression in zip(poses, expressions)
    }

    # get attr poses
    # dict where key is every attr for all joints we want to still have driven
    # and value is all poses that drive that attr
    attr_poses = {}

    for joint in pose_joints:
        for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
            joint_attr = "{}.{}".format(joint, attr)

            joint_poses = []

            for pose in poses:
                if joint_attr in pose.deltas:
                    joint_poses.append(pose)

            attr_poses[joint_attr] = joint_poses

    # create combo logic
    LOG.info("Creating combo logic...")

    combo_network_node = cmds.createNode(
        "network", name="combo_network"
    )

    for psd_pose in psd_poses.values():
        combo_node = cmds.createNode(
            "combinationShape",
            name="{}_combinationShape".format(psd_pose.pose.name)
        )

        for index, pose in enumerate(psd_pose.input_poses):
            # weight = psd_pose.input_weights[index]

            output_attr = expression_attrs[pose.index]

            cmds.connectAttr(
                output_attr,
                "{}.inputWeight[{}]".format(combo_node, index)
            )

        cmds.addAttr(
            combo_network_node, longName=psd_pose.pose.name, defaultValue=0.0
        )

        cmds.connectAttr(
            "{}.outputWeight".format(combo_node),
            "{}.{}".format(combo_network_node, psd_pose.pose.name)
        )

        expression_mapping[psd_pose.pose.name] = "{}.{}".format(combo_network_node, psd_pose.pose.name)

    # break joint connections
    LOG.info("Disconnecting joints...")

    for transform in transforms:
        for channel in "trs":
            for axis in "xyz":
                mhMayaUtils.break_connections("{}.{}{}".format(transform, channel, axis))

    # create base mesh and blendshape node
    LOG.info("Baking shapes...")

    base_mesh = cmds.duplicate(mesh, name="{}_baked".format(mesh))[0]
    cmds.parent(base_mesh, world=True)

    bs_node = cmds.deformer(base_mesh, type="blendShape")[0]

    target_group = cmds.createNode("transform", name="targets")
    cmds.hide(target_group)

    # bake core shapes
    targets = []
    pose_names = []

    # start progress bar
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Baking shapes...',
        maxValue=pose_count
    )

    for pose_index, pose in enumerate(poses):
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        # pose rig
        if pose_index in psd_poses:
            psd_pose = psd_poses[pose_index]
            psd_pose.pose_joints(summed=True)
            pose_name = psd_pose.pose.name
            pose = psd_pose
        else:
            pose.pose_joints()
            pose_name = pose.name
            pose_names.append(pose_name)

        # create shape
        if detailed_verbose:
            LOG.info("    {} - {}".format(pose_name, pose))

        target = cmds.duplicate(mesh, name=pose_name)[0]
        cmds.parent(target, target_group)
        targets.append(target)

        bmBlendshapeUtils.append_blendshape_targets(
            bs_node, base_mesh, target, default_weight=0.0
        )

        pose.reset_joints()

        # create in-betweens
        if pose_name in in_betweens:
            in_between_targets = []

            for ib_index in range(in_betweens[pose_name]):
                ib_value = float(ib_index + 1) / float(in_betweens[pose_name] + 1)
                ib_value = round(ib_value, 3)

                pose.pose_joints(blend=ib_value)

                in_between_target = cmds.duplicate(mesh, name=pose_name)[0]
                cmds.parent(in_between_target, target_group)
                in_between_targets.append(in_between_target)

                bmBlendshapeUtils.add_in_between_target(
                    bs_node, base_mesh, pose_name, in_between_target, ib_value
                )

                pose.reset_joints()

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # delete targets so we can edit the deltas
    if calculate_psd_deltas:
        cmds.refresh()
        cmds.delete(target_group)
        cmds.refresh()

        # calculate psd blendshape deltas and subtract
        LOG.info("Calculating PSD deltas...")

        cmds.progressBar(
            gMainProgressBar,
            edit=True,
            beginProgress=True,
            isInterruptable=True,
            status='Calculating PSD deltas...',
            maxValue=len(psd_poses.keys())
        )

        for pose_index, psd_pose in psd_poses.items():
            if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
                return False

            cmds.progressBar(gMainProgressBar, edit=True, step=1)

            if detailed_verbose:
                LOG.info("    {}".format(psd_pose.pose.name))

            src_targets = [
                pose.index for pose in psd_pose.input_poses
            ]

            weights = [1.0] * len(src_targets)

            bmBlendshape.un_combine_deltas(
                bs_node,
                src_targets,
                weights,
                psd_pose.pose.index,
                optimise=optimise,
            )

        cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

        # subtract input psds
        LOG.info("Calculating input PSD deltas...")

        # do this in order of least combos to most combos
        for combo_count in range(3, 10):
            for psd_pose in psd_poses.values():
                if len(psd_pose.input_poses) != combo_count:
                    continue

                if detailed_verbose:
                    LOG.info("    {}".format(psd_pose.pose.name))

                src_targets = [
                    pose.pose.index for pose in psd_pose.input_psd_poses
                ]

                weights = [1.0] * len(src_targets)

                bmBlendshape.un_combine_deltas(
                    bs_node,
                    src_targets,
                    weights,
                    psd_pose.pose.index,
                    optimise=optimise,
                )

    # connect expression attrs
    if connect_shapes:
        if not expressions:
            LOG.info("No expressions to connect to blendShapes")
            return

        LOG.info("Connecting expression attrs...")

        for pose_name, expression_attr in expression_mapping.items():
            cmds.connectAttr(
                expression_attr,
                "{}.{}".format(bs_node, pose_name)
            )

    # create joint pose nodes
    LOG.info("Creating joint poses...")

    for attr, poses in attr_poses.items():
        if not poses:
            continue

        network_node = cmds.createNode(
            "network",
            name="{}_poses".format(attr.replace(".", "_"))
        )

        default = poses[0].defaults[attr]

        cmds.addAttr(
            network_node, longName="default", defaultValue=default
        )

        sum_node = cmds.createNode(
            "plusMinusAverage",
            name="{}_poseSum_plusMinusAverage".format(attr.replace(".", "_"))
        )

        cmds.connectAttr(
            "{}.default".format(network_node),
            "{}.input1D[0]".format(sum_node),
        )

        input_index = 1

        for pose in poses:
            if pose.deltas[attr] == 0.0:
                continue

            cmds.addAttr(
                network_node, longName=pose.name, defaultValue=0.0
            )

            mult_node = cmds.createNode(
                "multDoubleLinear",
                name="{}_pose{}_multDoubleLinear".format(attr.replace(".", "_"), input_index)
            )

            cmds.connectAttr(
                "{}.{}".format(network_node, pose.name),
                "{}.input1".format(mult_node)
            )

            cmds.setAttr(
                "{}.input2".format(mult_node),
                pose.deltas[attr]
            )

            cmds.connectAttr(
                "{}.output".format(mult_node),
                "{}.input1D[{}]".format(sum_node, input_index)
            )

            if pose.name in expression_mapping:
                cmds.connectAttr(
                    expression_mapping[pose.name],
                    "{}.{}".format(network_node, pose.name)
                )
            else:
                LOG.warning("no expression for {}".format(pose.name))

            input_index += 1

        # connect if we have more at least one input
        if input_index > 1:
            cmds.connectAttr(
                "{}.output1D".format(sum_node),
                attr
            )
        else:
            cmds.delete(network_node, sum_node)

    delete_redundant_joints(
        pose_joints=pose_joints, keep_joints=keep_joints
    )

    if rl4_nodes:
        cmds.delete(rl4_nodes)

    LOG.info("done.")

    return True
