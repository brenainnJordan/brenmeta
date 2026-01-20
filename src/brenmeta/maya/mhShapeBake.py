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
Convert pose system to pure blendshapes
"""
import time

from maya.api import OpenMaya
from maya import cmds
from maya import mel

from brenmeta.maya import mhBlendshape
from brenmeta.maya import mhMayaUtils
from brenmeta.core import mhCore

LOG = mhCore.get_basic_logger(__name__)

DEFAULT_IN_BETWEENS = [
    ("eyeBlinkL", 3),
    ("eyeBlinkR", 3),
    ("eyeLookLeftL", 1),
    ("eyeLookLeftR", 1),
    ("eyeLookRightL", 1),
    ("eyeLookRightR", 1),
    ("eyeLookUpL", 1),
    ("eyeLookUpR", 1),
    ("eyeLookDownL", 1),
    ("eyeLookDownR", 1),
    ("mouthLeft", 2),
    ("mouthRight", 2),
    ("mouthUpperLipBiteL", 1),
    ("mouthUpperLipBiteR", 1),
    ("mouthLowerLipBiteL", 1),
    ("mouthLowerLipBiteR", 1),
    ("tongueRoll", 2),
    # jaw and combos should share same number of in-betweens
    ("jawOpen", 3),
    ("mouthLipsTogetherUL", 3),
    ("mouthLipsTogetherUR", 3),
    ("mouthLipsTogetherDL", 3),
    ("mouthLipsTogetherDR", 3),
    ("MlipsTogether_Jopen_UL", 3),
    ("MlipsTogether_Jopen_UR", 3),
    ("MlipsTogether_Jopen_DL", 3),
    ("MlipsTogether_Jopen_DR", 3),
]

DEFAULT_IN_BETWEENS_DICT = {a: b for a, b in DEFAULT_IN_BETWEENS}

ADDITIONAL_SHAPES = [
    "eyeSquintL",
    "eyeSquintR",
]

ADDITIONAL_COMBOS = [
    # jawOpen
    ("jawOpen", "teethFwdD"),
    ("jawOpen", "teethBackD"),
    ("jawOpen", "teethUpD"),
    ("jawOpen", "teethDownD"),
    # ("jawOpen", "teethLeftD"),
    # ("jawOpen", "teethRightD"),
    ("jawOpen", "tongueUp"),
    ("jawOpen", "tongueDown"),
    ("jawOpen", "tongueOut"),
    ("jawOpen", "tongueBendUp"),
    ("jawOpen", "tongueBendDown"),
    ("jawOpen", "tongueTipUp"),
    ("jawOpen", "tonguePress"),

    # other brow
    ("browLateralL", "browRaiseInL"),
    ("browLateralR", "browRaiseInR"),

    # brows + blink
    ("browDownL", "eyeBlinkL"),
    ("browDownR", "eyeBlinkR"),
    ("browLateralL", "eyeBlinkL"),
    ("browLateralR", "eyeBlinkR"),
    # these combos are already present in the MH rig
    # ("browRaiseInL", "eyeBlinkL"),
    # ("browRaiseInR", "eyeBlinkR"),
    # ("browRaiseOuterL", "eyeBlinkL"),
    # ("browRaiseOuterR", "eyeBlinkR"),

    # eyeBlink + eyeSquint
    ("eyeSquintL", "eyeBlinkL"),
    ("eyeSquintR", "eyeBlinkR"),

    # brow + cheek raise
    ("browDownL", "eyeCheekRaiseL"),
    ("browDownR", "eyeCheekRaiseR"),
    ("browLateralL", "eyeCheekRaiseL"),
    ("browLateralR", "eyeCheekRaiseR"),

    # brows down + eye directions
    ("browDownL", "eyeLookLeftL"),
    ("browDownL", "eyeLookRightL"),
    ("browDownL", "eyeLookUpL"),
    ("browDownL", "eyeLookDownL"),
    ("browDownR", "eyeLookLeftR"),
    ("browDownR", "eyeLookRightR"),
    ("browDownR", "eyeLookUpR"),
    ("browDownR", "eyeLookDownR"),

    # brow lateral + eye directions
    ("browLateralL", "eyeLookLeftL"),
    ("browLateralL", "eyeLookRightL"),
    ("browLateralL", "eyeLookUpL"),
    ("browLateralL", "eyeLookDownL"),
    ("browLateralR", "eyeLookLeftR"),
    ("browLateralR", "eyeLookRightR"),
    ("browLateralR", "eyeLookUpR"),
    ("browLateralR", "eyeLookDownR"),

    # brow raise in + eye directions
    ("browRaiseInL", "eyeLookLeftL"),
    ("browRaiseInL", "eyeLookRightL"),
    ("browRaiseInL", "eyeLookUpL"),
    # ("browRaiseInL", "eyeLookDownL"), # already present
    ("browRaiseInR", "eyeLookLeftR"),
    ("browRaiseInR", "eyeLookRightR"),
    ("browRaiseInR", "eyeLookUpR"),
    # ("browRaiseInR", "eyeLookDownR"), # already present

    # brow raise out + eye directions
    ("browRaiseOuterL", "eyeLookLeftL"),
    ("browRaiseOuterL", "eyeLookRightL"),
    ("browRaiseOuterL", "eyeLookUpL"),
    # ("browRaiseOuterL", "eyeLookDownL"), # already present
    ("browRaiseOuterR", "eyeLookLeftR"),
    ("browRaiseOuterR", "eyeLookRightR"),
    ("browRaiseOuterR", "eyeLookUpR"),
    # ("browRaiseOuterR", "eyeLookDownR"), # already present

    # eyeCheekRaise + eye directions
    ("eyeCheekRaiseL", "eyeLookLeftL"),
    ("eyeCheekRaiseL", "eyeLookRightL"),
    ("eyeCheekRaiseL", "eyeLookUpL"),
    ("eyeCheekRaiseL", "eyeLookDownL"),
    ("eyeCheekRaiseR", "eyeLookLeftR"),
    ("eyeCheekRaiseR", "eyeLookRightR"),
    ("eyeCheekRaiseR", "eyeLookUpR"),
    ("eyeCheekRaiseR", "eyeLookDownR"),

    # eyeSquint + eye directions
    ("eyeSquintL", "eyeLookLeftL"),
    ("eyeSquintL", "eyeLookRightL"),
    ("eyeSquintL", "eyeLookUpL"),
    ("eyeSquintL", "eyeLookDownL"),
    ("eyeSquintR", "eyeLookLeftR"),
    ("eyeSquintR", "eyeLookRightR"),
    ("eyeSquintR", "eyeLookUpR"),
    ("eyeSquintR", "eyeLookDownR"),

    # noseWrinkleUpper + eye directions
    ("noseWrinkleUpperL", "eyeLookLeftL"),
    ("noseWrinkleUpperL", "eyeLookRightL"),
    ("noseWrinkleUpperL", "eyeLookUpL"),
    ("noseWrinkleUpperL", "eyeLookDownL"),
    ("noseWrinkleUpperR", "eyeLookLeftR"),
    ("noseWrinkleUpperR", "eyeLookRightR"),
    ("noseWrinkleUpperR", "eyeLookUpR"),
    ("noseWrinkleUpperR", "eyeLookDownR"),

]

POSE_JOINTS = [
    "FACIAL_L_Eye",
    "FACIAL_L_EyeParallel",
    "FACIAL_L_Pupil",
    "FACIAL_R_Eye",
    "FACIAL_R_EyeParallel",
    "FACIAL_R_Pupil",
    "FACIAL_C_Jaw",
    "FACIAL_C_LowerLipRotation",
    "FACIAL_C_TeethUpper",
    "FACIAL_C_TeethLower",
    # tongue
    "FACIAL_C_Tongue1",
    "FACIAL_C_Tongue2",
    "FACIAL_C_Tongue3",
    "FACIAL_C_Tongue4",
    "FACIAL_L_TongueSide1",
    "FACIAL_R_TongueSide1",
    "FACIAL_L_TongueSide2",
    "FACIAL_R_TongueSide2",
    "FACIAL_L_TongueSide3",
    "FACIAL_R_TongueSide3",
    "FACIAL_L_TongueSide4",
    "FACIAL_R_TongueSide4",
    "FACIAL_C_TongueUpper1",
    "FACIAL_C_TongueUpper2",
    "FACIAL_C_TongueUpper3",
    "FACIAL_C_TongueLower3",
]

KEEP_JOINTS = [
    "FACIAL_C_FacialRoot",
    "head",
    "neck_02",
    "neck_01",
    "spine_05",
    "spine_04",
]

DELETE = [
    "eyelashes_lod0_mesh",
    "eyeEdge_lod0_mesh",
    "cartilage_lod0_mesh",
    "eyeshell_lod0_mesh",
    "head_lod1_grp",
    "head_lod2_grp",
    "head_lod3_grp",
    "head_lod4_grp",
    "head_lod5_grp",
    "head_lod6_grp",
    "head_lod7_grp",
]

ROOT_JOINTS = [
    "FACIAL_C_Neck2Root",
    "FACIAL_C_Neck1Root",
    "FACIAL_C_FacialRoot",
]


def delete_redundant_joints(keep_joints=KEEP_JOINTS, pose_joints=POSE_JOINTS):
    joints = cmds.ls(type="joint")
    joints = [i for i in joints if i not in keep_joints + pose_joints]
    cmds.delete(joints)


def bake_shapes_from_dna_v1(
        dna_file,
        name="poseSystem",
        expressions_node="CTRL_expressions",
        in_betweens=DEFAULT_IN_BETWEENS_DICT,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        pose_joints=POSE_JOINTS,
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
    from brenmeta.dna1 import mhBehaviour
    from brenmeta.dna1 import mhSrc

    import dna_viewer, dnacalib

    mhSrc.validate_plugin()

    # load dna data
    LOG.info("Loading dna: {}".format(dna_file))

    dna_obj = dna_viewer.DNA(dna_file)

    LOG.info("Getting reader...")
    calib_reader = dnacalib.DNACalibDNAReader(dna_obj.reader)

    # get pose data
    LOG.info("Getting pose data...")

    poses = mhBehaviour.get_all_poses(calib_reader)
    psd_poses = mhBehaviour.get_psd_poses(calib_reader, poses)
    joints_attr_defaults = mhBehaviour.get_joint_defaults(calib_reader)

    convert_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh=mesh,
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        optimise=optimise,
        name=name,
        expressions_node=expressions_node,
        in_betweens=in_betweens,
        pose_joints=pose_joints,
        keep_joints=keep_joints,
        additional_combos=additional_combos,
        detailed_verbose=detailed_verbose
    )

    return True


def bake_shapes_from_dna_v2(
        dna_file,
        # name="poseSystem",
        expressions_node="CTRL_expressions",
        in_betweens=DEFAULT_IN_BETWEENS_DICT,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        pose_joints=POSE_JOINTS,
        keep_joints=KEEP_JOINTS,
        additional_combos=ADDITIONAL_COMBOS,
        use_combo_network=False,
        detailed_verbose=False
):
    """
from brenmy.mh.presets import bmMhFaceShapeBake

dna_file = r"D:/Projects/3d/metahuman/chloe/MHC_DCC_Export/MHC_chloe/head.dna"

bmMhFaceShapeBake.bake_shapes_from_dna_v2(
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
    from brenmeta.dna2 import mhBehaviour
    from brenmeta.dna2 import mhSrc

    import dnacalib2
    from mh_assemble_lib.model.dnalib import DNAReader, Layer

    mhSrc.validate_plugin()

    # load dna data
    LOG.info("Loading dna: {}".format(dna_file))

    dna_obj = DNAReader.read(dna_file, Layer.all)

    LOG.info("Getting reader...")
    calib_reader = dnacalib2.DNACalibDNAReader(dna_obj._reader)

    # get pose data
    LOG.info("Getting pose data...")

    poses = mhBehaviour.get_all_poses(calib_reader)
    psd_poses = mhBehaviour.get_psd_poses(calib_reader, poses)
    joints_attr_defaults = mhBehaviour.get_joint_defaults(calib_reader)

    convert_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh=mesh,
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        optimise=optimise,
        # name=name,
        expressions_node=expressions_node,
        in_betweens=in_betweens,
        pose_joints=pose_joints,
        keep_joints=keep_joints,
        additional_combos=additional_combos,
        use_combo_network=use_combo_network,
        detailed_verbose=detailed_verbose,
    )

    # cleanup
    rl4_nodes = cmds.ls(type="embeddedNodeRL4")

    if rl4_nodes:
        cmds.delete(rl4_nodes)

    return True


def break_joint_connections(root_joints=ROOT_JOINTS):
    transforms = []

    for root_joint in root_joints:
        transforms += cmds.listRelatives(root_joint, allDescendents=True, type="joint")

    for transform in transforms:
        for channel in "trs":
            for axis in "xyz":
                mhMayaUtils.break_connections("{}.{}{}".format(transform, channel, axis))

    return True


def create_combo_logic(poses, psd_poses, expressions_node, use_combo_network=True):
    # get expressions
    expressions = cmds.listAttr(expressions_node, userDefined=True)

    # create driver mapping
    driver_mapping = {}

    for pose in poses:
        if pose.name in expressions:
            driver_mapping[pose.name] = "{}.{}".format(expressions_node, pose.name)
        else:
            pass
            # LOG.warning("pose not found on {}: {}".format(expressions_node, pose.name))

    # create combo logic
    if use_combo_network:
        combo_network_node = cmds.createNode(
            "network", name="combo_network"
        )
    else:
        combo_network_node = None

    for psd_pose in psd_poses.values():
        combo_node = cmds.createNode(
            "combinationShape",
            name="{}_combinationShape".format(psd_pose.pose.name)
        )

        combo_valid = True

        for index, pose in enumerate(psd_pose.input_poses):
            # weight = psd_pose.input_weights[index]

            if pose.name not in driver_mapping:
                combo_valid = False
                break

            output_attr = driver_mapping[pose.name]

            cmds.connectAttr(
                output_attr,
                "{}.inputWeight[{}]".format(combo_node, index)
            )

        if not combo_valid:
            LOG.warning("combo not valid: {}".format(psd_pose.pose.name))
            cmds.delete(combo_node)
            continue

        if use_combo_network:
            # map via combo network node
            cmds.addAttr(
                combo_network_node, longName=psd_pose.pose.name, defaultValue=0.0
            )

            cmds.connectAttr(
                "{}.outputWeight".format(combo_node),
                "{}.{}".format(combo_network_node, psd_pose.pose.name)
            )

            driver_mapping[psd_pose.pose.name] = "{}.{}".format(combo_network_node, psd_pose.pose.name)
        else:
            # map to combo node directly
            driver_mapping[psd_pose.pose.name] = "{}.outputWeight".format(combo_node)

    return driver_mapping


def create_joint_poses(poses, pose_joints, driver_mapping):
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

            if pose.name in driver_mapping:
                cmds.connectAttr(
                    driver_mapping[pose.name],
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

    return True


def bake_shapes_from_poses(mesh, poses, psd_poses, in_betweens, detailed_verbose=True):
    base_mesh = cmds.duplicate(mesh, name="{}_baked".format(mesh))[0]

    bs_node = cmds.deformer(
        base_mesh, type="blendShape", name="{}_blendShape".format(mesh)
    )[0]

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
        maxValue=len(poses)
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

        mhBlendshape.append_blendshape_targets(
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

                mhBlendshape.add_in_between_target(
                    bs_node, base_mesh, pose_name, in_between_target, ib_value
                )

                pose.reset_joints()

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return base_mesh, bs_node, target_group


def calculate_psd_deltas(bs_node, psd_poses, in_betweens, detailed_verbose=True, optimise=True):
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

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

        mhBlendshape.un_combine_deltas(
            bs_node,
            src_targets,
            weights,
            psd_pose.pose.index,
            optimise=optimise,
        )

        if psd_pose.pose.name in in_betweens:
            in_between_count = in_betweens[psd_pose.pose.name]
            in_between_targets = []

            for ib_index in range(in_between_count):
                # uncombine in-between
                mhBlendshape.un_combine_deltas(
                    bs_node,
                    src_targets,
                    weights,
                    psd_pose.pose.index,
                    optimise=optimise,
                    in_between=ib_index
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

            mhBlendshape.un_combine_deltas(
                bs_node,
                src_targets,
                weights,
                psd_pose.pose.index,
                optimise=optimise,
            )

    return True


def convert_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        # name="poseSystem",
        expressions_node="CTRL_expressions",
        use_combo_network=False,
        in_betweens=DEFAULT_IN_BETWEENS,
        pose_joints=POSE_JOINTS,
        keep_joints=KEEP_JOINTS,
        additional_combos=ADDITIONAL_COMBOS,
        delete=DELETE,
        detailed_verbose=False
):
    """
    TODO support more than one mesh
    """

    # create additional combos
    if additional_combos:
        LOG.info("Adding additional combos...")

        mhCore.add_additional_combo_poses(
            poses, psd_poses, additional_combos, joints_attr_defaults
        )

    # break joint connections
    LOG.info("Disconnecting joints...")

    break_joint_connections()

    # create base mesh and blendshape node
    LOG.info("Baking shapes...")

    base_mesh, bs_node, target_group = bake_shapes_from_poses(
        mesh, poses, psd_poses, in_betweens, detailed_verbose=detailed_verbose
    )

    # delete targets so we can edit the deltas
    if calculate_psds:
        cmds.refresh()
        cmds.delete(target_group)
        cmds.refresh()

        # calculate psd blendshape deltas and subtract
        LOG.info("Calculating PSD deltas...")

        calculate_psd_deltas(
            bs_node, psd_poses, in_betweens, detailed_verbose=True, optimise=optimise
        )

    # create combo logic
    driver_mapping = create_combo_logic(
        poses, psd_poses, expressions_node,
        use_combo_network=use_combo_network
    )

    # connect expression attrs
    if connect_shapes:
        LOG.info("Connecting expression attrs...")

        for pose_name, driver_attr in driver_mapping.items():
            cmds.connectAttr(
                driver_attr,
                "{}.{}".format(bs_node, pose_name)
            )

    # create joint pose nodes
    LOG.info("Creating joint poses...")

    create_joint_poses(poses, pose_joints, driver_mapping)

    # cleanup
    delete_redundant_joints(
        pose_joints=pose_joints, keep_joints=keep_joints
    )

    cmds.delete(mesh)
    cmds.rename(base_mesh, mesh)

    if delete:
        cmds.delete(delete)

    LOG.info("done.")

    return True


def reconnect_shapes(
        poses,
        psd_poses,
        bs_node,
        joints_attr_defaults,
        expressions_node="CTRL_expressions",
        additional_shapes=ADDITIONAL_SHAPES,
        additional_combos=ADDITIONAL_COMBOS,
        use_combo_network=False,
        add_missing_targets=True,
):
    """TODO support multiple blendshape nodes
    """
    # create additional poses
    if additional_shapes:
        mhCore.add_additional_shapes(
            poses, additional_shapes, joints_attr_defaults
        )

    # create additional combos
    if additional_combos:
        LOG.info("Adding additional combos...")

        mhCore.add_additional_combo_poses(
            poses, psd_poses, additional_combos, joints_attr_defaults
        )

    # delete old combo network
    if cmds.objExists("combo_network"):
        cmds.delete("combo_network")

    # create combo logic
    driver_mapping = create_combo_logic(
        poses, psd_poses, expressions_node,
        use_combo_network=use_combo_network
    )

    # connect expression attrs
    LOG.info("Connecting expression attrs...")

    base_mesh = cmds.blendShape(bs_node, query=True, geometry=True)[0]

    for pose_name, driver_attr in driver_mapping.items():
        if mhBlendshape.get_blendshape_target_index(bs_node, pose_name) is None:
            if add_missing_targets:
                LOG.info("Adding target: {}".format(pose_name))

                mhBlendshape.create_empty_target(
                    base_mesh, bs_node, pose_name, default=0.0
                )
            else:
                continue

        cmds.connectAttr(
            driver_attr,
            "{}.{}".format(bs_node, pose_name)
        )

    return True
