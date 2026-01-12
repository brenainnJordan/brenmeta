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

DEFAULT_IN_BETWEENS_DICT = {a:b for a, b in DEFAULT_IN_BETWEENS}

ADDITIONAL_COMBOS = [
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


def delete_redundant_joints(keep_joints=KEEP_JOINTS, pose_joints=POSE_JOINTS):
    joints = cmds.ls(type="joint")
    joints = [i for i in joints if i not in keep_joints+pose_joints]
    cmds.delete(joints)


def bake_shapes_from_dna_v1(
        dna_file,
        name="poseSystem",
        expressions_node="CTRL_expressions",
        in_betweens=DEFAULT_IN_BETWEENS_DICT,
        mesh="head_lod0_mesh",
        calculate_psd_deltas=True,
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

    bake_shapes_from_poses(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh=mesh,
        calculate_psd_deltas=calculate_psd_deltas,
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
        name="poseSystem",
        expressions_node="CTRL_expressions",
        in_betweens=DEFAULT_IN_BETWEENS_DICT,
        mesh="head_lod0_mesh",
        calculate_psd_deltas=True,
        connect_shapes=True,
        optimise=True,
        pose_joints=POSE_JOINTS,
        keep_joints=KEEP_JOINTS,
        additional_combos=ADDITIONAL_COMBOS,
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

    bake_shapes_from_poses(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh=mesh,
        calculate_psd_deltas=calculate_psd_deltas,
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

    # cleanup
    rl4_nodes = cmds.ls(type="embeddedNodeRL4")

    if rl4_nodes:
        cmds.delete(rl4_nodes)

    return True


def bake_shapes_from_poses(
        poses,
        psd_poses,
        joints_attr_defaults,
        mesh="head_lod0_mesh",
        calculate_psd_deltas=True,
        connect_shapes=True,
        optimise=True,
        name="poseSystem",
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
    pose_count = len(poses)

    if additional_combos:
        LOG.info("Adding additional combos...")

        pose_dict = {
            pose.name: pose for pose in poses
        }

        for i, pose_names in enumerate(additional_combos):
            combo = mhCore.PSDPose()

            combo.pose = mhCore.Pose()
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

    # break joint connections
    LOG.info("Disconnecting joints...")

    for transform in transforms:
        for channel in "trs":
            for axis in "xyz":
                mhMayaUtils.break_connections("{}.{}{}".format(transform, channel, axis))

    # create base mesh and blendshape node
    LOG.info("Baking shapes...")

    base_mesh = cmds.duplicate(mesh, name="{}_baked".format(mesh))[0]

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
                    # ib_value = float(ib_index + 1) / float(in_between_count + 1)
                    # ib_value = round(ib_value, 3)

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

    # connect expression attrs
    if connect_shapes:
        if not expressions:
            LOG.info("No expressions to connect to blendShapes")
            return

        LOG.info("Connecting expression attrs...")

        for pose_name, expression_attr in driver_mapping.items():
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
