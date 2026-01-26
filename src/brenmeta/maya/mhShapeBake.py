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
import json

from maya.api import OpenMaya
from maya import cmds
from maya import mel

from brenmeta.maya import mhBlendshape
from brenmeta.maya import mhMayaUtils
from brenmeta.core import mhCore

LOG = mhCore.get_basic_logger(__name__)

COMBO_NET = "combo_network"


class BakeConfig(object):
    def __init__(self):
        self.shapes = None
        self.in_betweens = None
        self.combos = None
        self.pose_joints = None
        self.keep_joints = None
        self.delete = None
        self.root_joints = None

    @classmethod
    def load(cls, file_path):
        config = cls()

        data = None

        with open(file_path, 'r') as f:
            if f:
                data = json.load(f)

        if not data:
            raise mhCore.MHError(
                "Failed to load config: {}".format(file_path)
            )

        config.shapes = data["shapes"]
        config.in_betweens = data["in_betweens"]
        config.pose_joints = data["pose_joints"]
        config.keep_joints = data["keep_joints"]
        config.delete = data["delete"]
        config.root_joints = data["root_joints"]

        config.combos = [
            combo for combo_data in data["combos"]
            for combo in combo_data["combos"]
            if combo_data["enabled"]
        ]

        print("test", config.combos)

        return config


def delete_redundant_joints(keep_joints, pose_joints):
    joints = cmds.ls(type="joint")
    joints = [i for i in joints if i not in keep_joints + pose_joints]
    cmds.delete(joints)


def bake_shapes_from_dna_v1(
        dna_file,
        bake_config_file,
        name="poseSystem",
        expressions_node="CTRL_expressions",
        # in_betweens=DEFAULT_IN_BETWEENS,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        # pose_joints=POSE_JOINTS,
        # keep_joints=KEEP_JOINTS,
        # additional_combos=ADDITIONAL_COMBOS,
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

    bake_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        bake_config_file,
        mesh=mesh,
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        optimise=optimise,
        name=name,
        expressions_node=expressions_node,
        # in_betweens=in_betweens,
        # pose_joints=pose_joints,
        # keep_joints=keep_joints,
        # additional_combos=additional_combos,
        detailed_verbose=detailed_verbose
    )

    return True


def bake_shapes_from_dna_v2(
        dna_file,
        # name="poseSystem",
        bake_config_file,
        expressions_node="CTRL_expressions",
        # in_betweens=DEFAULT_IN_BETWEENS,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        # pose_joints=POSE_JOINTS,
        # keep_joints=KEEP_JOINTS,
        # additional_combos=ADDITIONAL_COMBOS,
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

    bake_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        bake_config_file,
        mesh=mesh,
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        optimise=optimise,
        # name=name,
        expressions_node=expressions_node,
        # in_betweens=in_betweens,
        # pose_joints=pose_joints,
        # keep_joints=keep_joints,
        # additional_combos=additional_combos,
        use_combo_network=use_combo_network,
        detailed_verbose=detailed_verbose,
    )

    # cleanup
    rl4_nodes = cmds.ls(type="embeddedNodeRL4")

    if rl4_nodes:
        cmds.delete(rl4_nodes)

    return True


def break_joint_connections(root_joints):
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
    # TODO investigate why combos aren't connecting
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


def bake_rig(
        poses,
        psd_poses,
        joints_attr_defaults,
        config_file_path,
        mesh="head_lod0_mesh",
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
        # name="poseSystem",
        expressions_node="CTRL_expressions",
        use_combo_network=False,
        # in_betweens=DEFAULT_IN_BETWEENS,
        # pose_joints=POSE_JOINTS,
        # keep_joints=KEEP_JOINTS,
        # additional_combos=ADDITIONAL_COMBOS,
        # delete=DELETE,
        detailed_verbose=False
):
    """
    TODO support more than one mesh
    TODO additional shapes
    """

    # load config
    bake_config = BakeConfig.load(config_file_path)

    # create additional poses
    if bake_config.shapes:
        mhCore.add_additional_shapes(
            poses, bake_config.shapes, joints_attr_defaults
        )

    # create additional combos
    if bake_config.combos:
        LOG.info("Adding additional combos...")

        mhCore.add_additional_combo_poses(
            poses, psd_poses, bake_config.combos, joints_attr_defaults
        )

    # break joint connections
    LOG.info("Disconnecting joints...")

    break_joint_connections(bake_config.root_joints)

    # create base mesh and blendshape node
    LOG.info("Baking shapes...")

    base_mesh, bs_node, target_group = bake_shapes_from_poses(
        mesh, poses, psd_poses, bake_config.in_betweens, detailed_verbose=detailed_verbose
    )

    # delete targets so we can edit the deltas
    if calculate_psds:
        cmds.refresh()
        cmds.delete(target_group)
        cmds.refresh()

        # calculate psd blendshape deltas and subtract
        LOG.info("Calculating PSD deltas...")

        calculate_psd_deltas(
            bs_node, psd_poses, bake_config.in_betweens, detailed_verbose=True, optimise=optimise
        )

    # delete original mesh
    cmds.delete(mesh)
    cmds.rename(base_mesh, mesh)

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

    create_joint_poses(poses, bake_config.pose_joints, driver_mapping)

    # cleanup
    delete_redundant_joints(
        bake_config.pose_joints,
        bake_config.keep_joints
    )

    if bake_config.delete:
        cmds.delete(bake_config.delete)

    LOG.info("done.")

    return True


def disconnect(
        bs_nodes,
        disconnect_targets=True,
        disconnect_joints=True,
        delete_combo_network=True,
        verbose=True
):
    # disconnect blendshapes
    if disconnect_targets:
        for bs_node in bs_nodes:
            if verbose:
                LOG.info("Disconnecting blendshape targets: {}".format(bs_node))

            targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

            for target in targets:
                target_attr = "{}.{}".format(bs_node, target)

                cons = cmds.listConnections(
                    target_attr, source=True, destination=False, plugs=True
                )

                if cons:
                    cmds.disconnectAttr(cons[0], target_attr)

    # disconnect joints and delete networks
    if disconnect_joints:
        if verbose:
            LOG.info("Disconnecting joints")

        pose_nets = cmds.ls("*_poses", type="network")
        cmds.delete(pose_nets)

    if delete_combo_network:
        # delete combo network
        if cmds.objExists(COMBO_NET):
            if verbose:
                LOG.info("deleting node: {}".format(COMBO_NET))

            cmds.delete(COMBO_NET)

    return True


def reconnect(
        poses,
        psd_poses,
        bs_node,
        joints_attr_defaults,
        config_file_path,
        # pose_joints=POSE_JOINTS,
        expressions_node="CTRL_expressions",
        # additional_shapes=ADDITIONAL_SHAPES,
        # additional_combos=ADDITIONAL_COMBOS,
        reconnect_joints=True,
        reconnect_targets=True,
        use_combo_network=False,
        add_missing_targets=True,
):
    """TODO support multiple blendshape nodes
    """
    # load config
    bake_config = BakeConfig.load(config_file_path)

    # create additional poses
    if bake_config.shapes:
        mhCore.add_additional_shapes(
            poses, bake_config.shapes, joints_attr_defaults
        )

    # create additional combos
    if bake_config.combos:
        LOG.info("Adding additional combos...")

        mhCore.add_additional_combo_poses(
            poses, psd_poses, bake_config.combos, joints_attr_defaults
        )

    # create combo logic
    LOG.info("Creating combo logic")

    driver_mapping = create_combo_logic(
        poses, psd_poses, expressions_node,
        use_combo_network=use_combo_network
    )

    # connect expression attrs

    if reconnect_targets or add_missing_targets:
        LOG.info("Connecting expression attrs...")

        base_mesh = cmds.blendShape(bs_node, query=True, geometry=True)[0]

        for pose_name, driver_attr in driver_mapping.items():
            if mhBlendshape.get_blendshape_target_index(bs_node, pose_name) is None:
                if add_missing_targets:
                    LOG.info("Adding target: {}.{}".format(bs_node, pose_name))

                    mhBlendshape.create_empty_target(
                        base_mesh, bs_node, pose_name, default=0.0
                    )
                else:
                    LOG.info("Missing target: {}.{}".format(bs_node, pose_name))
                    continue

            if reconnect_targets:
                cmds.connectAttr(
                    driver_attr,
                    "{}.{}".format(bs_node, pose_name)
                )

    if reconnect_joints:
        LOG.info("Reconnecting joints")
        # connecting joints
        create_joint_poses(poses, pose_joints, driver_mapping)

    return True
