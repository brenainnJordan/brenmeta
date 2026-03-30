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
Convert metahuman rig to pure blendshapes and native maya nodes
"""

import time
import json
import math
import numpy

from maya.api import OpenMaya
from maya import cmds
from maya import mel

from brenmeta.maya import mhBlendshape
from brenmeta.maya import mhMayaUtils
from brenmeta.core import mhCore
from brenmeta.maya.mhMayaUtils import points_equal

LOG = mhCore.get_basic_logger(__name__)

COMBO_NET = "combo_network"
READER_GROUP = "reader_grp"


class BakeConfig(object):
    """Convenience object to load and manage bake config data

    mesh_blendshapes: list of lists
        [
            [<mesh>, <blendshape node>],
            ...
        ]

    shapes: list of additional targets
        [
            "eyeSquintL",
            ...
        ]

    in_betweens: dict
        {
            <target>: <number of in-betweens>,
            ...
        }

    combos: list of dicts
        [
            {
                "description": "brief human-readable description",
                "enabled": true,
                "combos": [
                    ["jawOpen", "teethFwdD"],
                    ...
                ]
            },
            ...
        ]

    pose_joints: list of joints used for posing the rig

    keep_joints: list of joints in addition to pose_joints to keep

    delete: list of other nodes to delete after bake

    root_joints: list of root joints to parse hierarchy

    """

    def __init__(self):
        self.mesh_blendshapes = None
        self.shapes = None
        self.in_betweens = None
        self.combos = None
        self.pose_joints = None
        self.keep_joints = None
        self.delete = None
        self.root_joints = None
        self.readers = None

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

        config.mesh_blendshapes = data["mesh_blendshapes"]
        # config.shapes = data["shapes"]
        config.in_betweens = data["in_betweens"]
        config.pose_joints = data["pose_joints"]
        config.keep_joints = data["keep_joints"]
        config.delete = data["delete"]
        config.root_joints = data["root_joints"]
        config.readers = data["readers"]

        # parse additional shapes and optionally their in-betweens
        if data["shapes"]:
            config.shapes = []

            for shape in data["shapes"]:
                if isinstance(shape, list):
                    shape, in_betweens = shape
                    config.shapes.append(shape)
                    config.in_betweens[shape] = in_betweens
                else:
                    config.shapes.append(shape)

        config.combos = [
            combo for combo_data in data["combos"]
            for combo in combo_data["combos"]
            if combo_data["enabled"]
        ]

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
        calculate_psds=True,
        connect_shapes=True,
        optimise=True,
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
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        optimise=optimise,
        expressions_node=expressions_node,
        detailed_verbose=detailed_verbose
    )

    return True


def bake_shapes_from_dna_v2(
        dna_file,
        bake_config_file,
        expressions_node="CTRL_expressions",
        bake_shapes=True,
        calculate_psds=True,
        connect_shapes=True,
        connect_joints=True,
        optimise=True,
        cleanup=True,
        use_combo_network=False,
        detailed_verbose=False
):
    """
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
        bake_shapes=bake_shapes,
        calculate_psds=calculate_psds,
        connect_shapes=connect_shapes,
        connect_joints=connect_joints,
        optimise=optimise,
        cleanup=cleanup,
        expressions_node=expressions_node,
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


def create_cone_reader(transform, parent_space_transform, name, vector, rotation, group, smooth=True):
    """
    TODO connect message attributes so nodes can be safely deleted later
    """

    default_transform = "{}_readerDefault_grp".format(transform)

    if not cmds.objExists(default_transform):
        cmds.createNode(
            "transform", name=default_transform, parent=group
        )

        matrix = cmds.xform(transform, query=True, matrix=True, worldSpace=True)
        cmds.xform(default_transform, matrix=matrix, worldSpace=True)

        cmds.parentConstraint(
            parent_space_transform, default_transform, maintainOffset=True
        )

    cone_transform = cmds.createNode(
        "transform",
        name="{}_readerCone_grp".format(name),
        parent=default_transform
    )

    cmds.xform(cone_transform, rotation=rotation)

    # default vector
    default_vector_product = cmds.createNode(
        "vectorProduct", name="{}_default_vectorProduct".format(name)
    )

    cmds.setAttr("{}.input1".format(default_vector_product), *vector)

    cmds.connectAttr(
        "{}.worldMatrix[0]".format(default_transform),
        "{}.matrix".format(default_vector_product)
    )

    cmds.setAttr("{}.operation".format(default_vector_product), 3)

    # transform vector
    transform_vector_product = cmds.createNode(
        "vectorProduct", name="{}_transform_vectorProduct".format(name)
    )

    cmds.setAttr("{}.input1".format(transform_vector_product), *vector)

    cmds.connectAttr(
        "{}.worldMatrix[0]".format(transform),
        "{}.matrix".format(transform_vector_product)
    )

    cmds.setAttr("{}.operation".format(transform_vector_product), 3)

    # cone vector
    cone_vector_product = cmds.createNode(
        "vectorProduct", name="{}_cone_vectorProduct".format(name)
    )

    cmds.setAttr("{}.input1".format(cone_vector_product), *vector)

    cmds.connectAttr(
        "{}.worldMatrix[0]".format(cone_transform),
        "{}.matrix".format(cone_vector_product)
    )

    cmds.setAttr("{}.operation".format(cone_vector_product), 3)

    # cone angle
    cone_angle_between = cmds.createNode(
        "angleBetween", name="{}_cone_angleBetween".format(name)
    )

    cmds.connectAttr(
        "{}.output".format(transform_vector_product),
        "{}.vector1".format(cone_angle_between)
    )

    cmds.connectAttr(
        "{}.output".format(cone_vector_product),
        "{}.vector2".format(cone_angle_between)
    )

    # default angle
    default_angle_between = cmds.createNode(
        "angleBetween", name="{}_default_angleBetween".format(name)
    )

    cmds.connectAttr(
        "{}.output".format(default_vector_product),
        "{}.vector1".format(default_angle_between)
    )

    cmds.connectAttr(
        "{}.output".format(cone_vector_product),
        "{}.vector2".format(default_angle_between)
    )

    # remap
    remap = cmds.createNode(
        "remapValue",
        name="{}_reader_remapValue".format(name)
    )

    cmds.connectAttr(
        "{}.angle".format(default_angle_between),
        "{}.inputMin".format(remap)
    )

    cmds.connectAttr(
        "{}.angle".format(cone_angle_between),
        "{}.inputValue".format(remap)
    )

    cmds.setAttr(
        "{}.inputMax".format(remap), 0.0
    )

    cmds.setAttr(
        "{}.outputMin".format(remap), 0.0
    )

    cmds.setAttr(
        "{}.outputMax".format(remap), 1.0
    )

    if smooth:
        cmds.setAttr(
            "{}.value[0].value_Interp".format(remap), 2
        )

    # connect message attributes for reference
    if not cmds.attributeQuery("nodes", node=group, exists=True):
        cmds.addAttr(
            group,
            longName="nodes",
            attributeType="message"
        )

    for node in [
        default_vector_product,
        transform_vector_product,
        cone_vector_product,
        default_angle_between,
        cone_angle_between,
        remap,
    ]:
        cmds.addAttr(
            node,
            longName="reader_group",
            attributeType="message"
        )

        cmds.connectAttr(
            "{}.nodes".format(group),
            "{}.reader_group".format(node)
        )

    return "{}.outValue".format(remap)


def create_driver_logic(
        poses, psd_poses, expressions_node, additional_shapes=None, use_combo_network=True, reader_configs=None
):
    # get expressions
    expressions = cmds.listAttr(expressions_node, userDefined=True)

    # add expression attrs for additional shapes
    if additional_shapes:
        for shape_name in additional_shapes:
            if shape_name not in expressions:
                LOG.info("Adding expression attr: {}.{}".format(expressions_node, shape_name))

                cmds.addAttr(
                    expressions_node,
                    longName=shape_name,
                    min=0.0,
                    max=1.0
                )

            expressions.append(shape_name)

    # create driver mapping for non-combo poses
    driver_mapping = {}

    for pose_index, pose in enumerate(poses):
        if pose_index in psd_poses or pose.name is None:
            continue

        if pose.name in expressions:
            driver_mapping[pose.name] = "{}.{}".format(expressions_node, pose.name)
        else:
            LOG.warning("Pose not found on expression node: {}".format(pose.name))

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

    # create readers
    if reader_configs:
        group = "headRig_grp"

        reader_group = cmds.createNode(
            "transform",
            name=READER_GROUP,
            parent=group
        )

        for reader_config in reader_configs:
            driver_attr = create_cone_reader(
                reader_config["transform"],
                reader_config["parent_space_transform"],
                reader_config["name"],
                reader_config["vector"],
                reader_config["rotation"],
                reader_group,
                smooth=reader_config["smooth"],
            )

            cmds.connectAttr(
                driver_attr,
                "{}.{}".format(expressions_node, reader_config["name"])
            )

    return driver_mapping


def connect_targets(driver_mapping, bs_nodes):
    for bs_node in bs_nodes:
        targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

        for pose_name, driver_attr in driver_mapping.items():

            if pose_name not in targets:
                continue

            cmds.connectAttr(
                driver_attr,
                "{}.{}".format(bs_node, pose_name)
            )

    return True


def create_joint_poses(poses, pose_joints, driver_mapping):
    # get attr poses
    # dict where key is every attr for all joints we want to still have driven
    # and value is all poses that drive that attr
    attr_poses = {}

    for joint in pose_joints:
        if not cmds.objExists(joint):
            LOG.warning("Joint not found: {}".format(joint))
            continue

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


def bake_shapes_from_poses(mesh_blendshapes, poses, psd_poses, in_betweens, detailed_verbose=True, skip_empty=True):
    """Pose rig and create blendshape targets for the given meshes
    """
    # get nodes
    meshes = [mesh for mesh, bs_node in mesh_blendshapes]
    bs_nodes = [bs_node for mesh, bs_node in mesh_blendshapes]

    # get neutral points
    neutral_points = [
        mhMayaUtils.get_points(mesh, as_numpy=True)
        for mesh in meshes
    ]

    # create base meshes
    base_meshes = [
        cmds.duplicate(mesh, name="{}_baked".format(mesh))[0]
        for mesh in meshes
    ]

    # create new blendshape nodes
    bs_nodes = [
        cmds.deformer(
            base_mesh, type="blendShape", name=bs_node
        )[0]
        for base_mesh, bs_node in zip(base_meshes, bs_nodes)
    ]

    # create groups
    target_groups = [
        cmds.createNode("transform", name="{}_targets".format(mesh))
        for mesh in meshes
    ]

    cmds.hide(target_groups)

    # bake core shapes
    targets_list = [[] for _ in meshes]

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

        for i, mesh in enumerate(meshes):
            base_mesh = base_meshes[i]
            bs_node = bs_nodes[i]
            points = neutral_points[i]
            target_group = target_groups[i]
            mesh_targets = targets_list[i]

            # check if mesh has actually changed shape
            target_points = mhMayaUtils.get_points(mesh, as_numpy=True)

            points_equal = mhMayaUtils.points_equal(points, target_points)

            # skip empty targets (excluding first mesh, assuming that's the head)
            if all([
                i > 0,
                skip_empty,
                points_equal,
            ]):
                continue

            # create target
            target = cmds.duplicate(mesh)[0]
            cmds.parent(target, target_group)
            target = cmds.rename(target, pose_name)
            mesh_targets.append(target)

            mhBlendshape.append_blendshape_targets(
                bs_node, base_mesh, target, default_weight=0.0
            )

        pose.reset_joints()

        # create in-betweens
        if pose_name in in_betweens:
            for ib_index in range(in_betweens[pose_name]):
                ib_value = float(ib_index + 1) / float(in_betweens[pose_name] + 1)
                ib_value = round(ib_value, 3)

                pose.pose_joints(blend=ib_value)

                for mesh, base_mesh, bs_node, target_group, mesh_targets in zip(
                        meshes, base_meshes, bs_nodes, target_groups, targets_list
                ):
                    # skip in-between if target has been skipped
                    if pose_name not in mesh_targets:
                        continue

                    in_between_target = cmds.duplicate(mesh, name=pose_name)[0]
                    cmds.parent(in_between_target, target_group)

                    mhBlendshape.add_in_between_target(
                        bs_node, base_mesh, pose_name, in_between_target, ib_value
                    )

                pose.reset_joints()

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return base_meshes, bs_nodes, target_groups


def calculate_psd_deltas(bs_node, psd_poses, in_betweens, detailed_verbose=True, optimise=True):
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    all_targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Calculating PSD deltas ({})...'.format(bs_node),
        maxValue=len(psd_poses.keys())
    )

    for pose_index, psd_pose in psd_poses.items():
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        # check if this target was skipped
        if psd_pose.pose.name not in all_targets:
            continue

        if detailed_verbose:
            LOG.info("    {}".format(psd_pose.pose.name))

        src_targets = [
            pose.name for pose in psd_pose.input_poses if pose.name in all_targets
        ]

        weights = [1.0] * len(src_targets)

        mhBlendshape.un_combine_deltas(
            bs_node,
            src_targets,
            weights,
            psd_pose.pose.name,
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
                    psd_pose.pose.name,
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
        bake_shapes=True,
        calculate_psds=True,
        connect_shapes=True,
        connect_joints=True,
        optimise=True,
        cleanup=True,
        expressions_node="CTRL_expressions",
        use_combo_network=False,
        detailed_verbose=False
):
    """
    """

    # load config
    bake_config = BakeConfig.load(config_file_path)

    meshes = [mesh for mesh, bs_node in bake_config.mesh_blendshapes]
    bs_nodes = [bs_node for mesh, bs_node in bake_config.mesh_blendshapes]

    # create additional poses
    if bake_config.shapes:
        LOG.info("Adding additional poses...")

        mhCore.add_additional_poses(
            poses, bake_config.shapes, joints_attr_defaults
        )

    # create additional combos
    if bake_config.combos:
        LOG.info("Adding additional combo poses...")

        mhCore.add_additional_combo_poses(
            poses, psd_poses, bake_config.combos, joints_attr_defaults
        )

    # break joint connections
    if bake_shapes or connect_joints:
        break_joint_connections(bake_config.root_joints)

    # create base mesh and blendshape node
    if bake_shapes:
        LOG.info("Disconnecting joints...")

        LOG.info("Baking shapes...")

        base_meshes, bs_nodes, target_groups = bake_shapes_from_poses(
            bake_config.mesh_blendshapes,
            poses,
            psd_poses,
            bake_config.in_betweens,
            detailed_verbose=detailed_verbose
        )

        # delete original meshes
        cmds.delete(meshes)

        # rename baked meshes
        for base_mesh, mesh in zip(base_meshes, meshes):
            cmds.rename(base_mesh, mesh)

        if cleanup:
            cmds.refresh()
            cmds.delete(target_groups)
            cmds.refresh()

    # delete targets so we can edit the deltas
    if calculate_psds:
        # calculate psd blendshape deltas and subtract
        LOG.info("Calculating PSD deltas...")

        for bs_node in bs_nodes:
            calculate_psd_deltas(
                bs_node,
                psd_poses,
                bake_config.in_betweens,
                detailed_verbose=True,
                optimise=optimise
            )

    # create combo logic
    if connect_shapes or connect_joints:
        LOG.info("Creating driver logic...")

        driver_mapping = create_driver_logic(
            poses,
            psd_poses,
            expressions_node,
            additional_shapes=bake_config.shapes,
            use_combo_network=use_combo_network,
            reader_configs=bake_config.readers
        )
    else:
        driver_mapping = None

    # connect expression attrs
    if connect_shapes:
        LOG.info("Connecting expression attrs...")

        connect_targets(driver_mapping, bs_nodes)

    # create joint pose nodes
    if connect_joints:
        LOG.info("Creating joint poses...")

        create_joint_poses(poses, bake_config.pose_joints, driver_mapping)

    # cleanup
    if cleanup:
        delete_redundant_joints(
            bake_config.pose_joints,
            bake_config.keep_joints
        )

        if bake_config.delete:
            delete_nodes = [i for i in bake_config.delete if cmds.objExists(i)]

            if delete_nodes:
                cmds.delete(delete_nodes)

    LOG.info("done.")

    return True


def disconnect(
        config_file_path,
        disconnect_targets=True,
        disconnect_joints=True,
        delete_combo_network=True,
        delete_readers=True,
        verbose=True
):
    # load config
    bake_config = BakeConfig.load(config_file_path)

    bs_nodes = [bs_node for mesh, bs_node in bake_config.mesh_blendshapes]

    # disconnect blendshapes
    if disconnect_targets:
        for bs_node in bs_nodes:
            if not cmds.objExists(bs_node):
                continue

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

    if delete_readers:
        # delete readers
        if cmds.objExists(READER_GROUP):
            nodes = cmds.listConnections("{}.nodes".format(READER_GROUP))

            if nodes:
                if verbose:
                    LOG.info("deleting reader nodes")

                cmds.delete(nodes)

            if verbose:
                LOG.info("deleting node: {}".format(READER_GROUP))

            cmds.delete(READER_GROUP)

    return True


def reconnect(
        poses,
        psd_poses,
        joints_attr_defaults,
        config_file_path,
        expressions_node="CTRL_expressions",
        reconnect_joints=True,
        reconnect_targets=True,
        use_combo_network=False,
        add_missing_targets=True,
):
    """
    """
    # load config
    bake_config = BakeConfig.load(config_file_path)

    bs_nodes = [
        bs_node for mesh, bs_node in bake_config.mesh_blendshapes if cmds.objExists(bs_node)
    ]

    # create additional poses
    if bake_config.shapes:
        LOG.info("Adding additional poses...")

        mhCore.add_additional_poses(
            poses, bake_config.shapes, joints_attr_defaults
        )

    # create additional combos
    if bake_config.combos:
        LOG.info("Adding additional combo poses...")

        _, _, new_psd_poses = mhCore.add_additional_combo_poses(
            poses, psd_poses, bake_config.combos, joints_attr_defaults
        )
    else:
        new_psd_poses = []

    # create combo logic
    LOG.info("Creating driver logic...")

    driver_mapping = create_driver_logic(
        poses,
        psd_poses,
        expressions_node,
        additional_shapes=bake_config.shapes,
        use_combo_network=use_combo_network,
        reader_configs=bake_config.readers
    )

    # add missing targets
    if add_missing_targets:
        for bs_node in bs_nodes:
            base_mesh = cmds.blendShape(bs_node, query=True, geometry=True)[0]

            new_shapes = list(bake_config.shapes)
            new_shapes += [psd_pose.pose.name for psd_pose in new_psd_poses]

            for shape_name in new_shapes:
                if mhBlendshape.get_blendshape_target_index(bs_node, shape_name) is not None:
                    continue

                LOG.info("Adding target: {}.{}".format(bs_node, shape_name))

                mhBlendshape.create_empty_target(
                    base_mesh, bs_node, shape_name, default=0.0
                )

                # add in-betweens
                if shape_name in bake_config.in_betweens:
                    ib_count = bake_config.in_betweens[shape_name]

                    for ib_index in range(ib_count):
                        ib_value = float(ib_index + 1) / float(ib_count + 1)
                        ib_value = round(ib_value, 3)

                        mhBlendshape.add_in_between_target(
                            bs_node, base_mesh, shape_name, None, ib_value
                        )

    # connect expression attrs
    if reconnect_targets:
        LOG.info("Connecting targets...")

        connect_targets(driver_mapping, bs_nodes)

    if reconnect_joints:
        LOG.info("Reconnecting joints")
        # connecting joints
        create_joint_poses(poses, bake_config.pose_joints, driver_mapping)

    return True


def extract_pose_correctives(poses, psd_poses, mesh, bs_node, skinned_mesh, rebuild=True):
    """
import dna
import dnacalib2
from mh_assemble_lib.model.dnalib import DNAReader, Layer

from brenmeta.maya import mhBlendshape
from brenmeta.dna2 import mhBehaviour

dna_path = r"D:\Projects\3d\metahuman\scansoup\head_016_male\head_016_male_01.dna"
mesh = "head_lod0_mesh"
bs_node = "head_lod0_blendShape"
skinned_mesh = "head_lod0_skinned"

dna_obj = DNAReader.read(dna_path, Layer.all)
calib_reader = dnacalib2.DNACalibDNAReader(dna_obj._reader)

poses = mhBehaviour.get_all_poses(calib_reader)
psd_poses = mhBehaviour.get_psd_poses(calib_reader, poses, override_name=True)
joints_attr_defaults = mhBehaviour.get_joint_defaults(calib_reader)

mhBlendshape.extract_pose_correctives(
    poses, psd_poses, mesh, bs_node, skinned_mesh, rebuild=True
)

    """
    # check mesh and skinned mesh are different
    if mesh == skinned_mesh:
        raise mhCore.MHError("Mesh and Skinned Mesh cannot be the same")

    # get skinned joints
    skin_cluster = mhMayaUtils.find_related_skin_cluster(skinned_mesh)

    driven_joints = cmds.skinCluster(skin_cluster, query=True, influence=True)

    # get targets
    targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

    # get points
    orig_mesh = mhMayaUtils.get_orig_mesh(bs_node, as_name=True)
    orig_points = mhMayaUtils.get_points(orig_mesh, as_numpy=True)

    # get parent of joints
    driven_joints = set(driven_joints)

    for joint in list(driven_joints):
        parents = mhMayaUtils.get_all_parents(joint)
        print(parents)
        driven_joints.update(parents)

    driven_joints = list(driven_joints)

    LOG.info("driven joints: {}".format(driven_joints))

    # temporarily disconnect all joints and targets in the scene
    LOG.info("disconnecting joints and targets")
    all_joints = cmds.ls(type="joint")
    joint_cons = mhMayaUtils.disconnect_transforms(all_joints)
    target_cons = mhMayaUtils.disconnect_attrs(bs_node, targets)

    # create groups
    group = cmds.createNode("transform", name="correctives_grp")

    if rebuild:
        target_group = cmds.createNode("transform", name="target_grp")
    else:
        target_group = None

    # start progress bar
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Extracting correctives...',
        maxValue=len(poses)
    )

    # loop through poses
    correctives = []
    correctives_dict = {}

    for i, pose in enumerate(poses):
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        if pose.name not in targets:
            continue

        pose_name = pose.name

        if i in psd_poses:
            pose = psd_poses[i]

        if not pose.affects_joints(driven_joints):
            continue

        # get data
        target_index = mhBlendshape.get_blendshape_target_index(bs_node, pose_name)
        plugs = mhBlendshape.BlendshapeTargetPlugs(bs_node, target_index)
        ib_values, ib_indices = plugs.get_inbetween_values()

        # loop through full value and inbetween values
        values = [1.0] + ib_values

        for index, value in enumerate(values):
            LOG.info("extracting corrective: {} at {}".format(pose_name, value))

            if value != 1.0:
                ib_value = value
                ib_index = index - 1
            else:
                ib_value = None
                ib_index = None

            # pose joints and turn on shape
            pose.pose_joints(blend=value)

            cmds.setAttr("{}.{}".format(bs_node, pose_name), value)

            # extract corrective
            inverted = cmds.invertShape(skinned_mesh, mesh)

            if ib_index is not None:
                inverted = cmds.rename(inverted, "{}_IB{}_corrective".format(pose_name, ib_index))
            else:
                inverted = cmds.rename(inverted, "{}_corrective".format(pose_name))

            cmds.parent(inverted, group)

            cmds.sets(inverted, edit=True, forceElement="initialShadingGroup")

            # add to list
            correctives.append(
                (pose, target_index, ib_index, ib_value, inverted)
            )

            if index == 1:
                correctives_dict[pose_name] = inverted

            # reset joints and shape
            pose.reset_joints()
            cmds.setAttr("{}.{}".format(bs_node, pose_name), 0.0)

    # calculate PSD targets
    # do this in order of least combos to most combos
    LOG.info("Calculating PSD deltas")

    for combo_count in range(2, 10):
        for pose, target_index, ib_index, ib_value, inverted in correctives:
            if not isinstance(pose, mhCore.PSDPose):
                continue

            if len(pose.input_poses) != combo_count:
                continue

            LOG.info("  {}".format(pose.pose.name))

            cmds.duplicate(inverted)

            points = mhMayaUtils.get_points(inverted, as_numpy=True)
            delta = points - orig_points

            # src_targets = [
            #     input_pose.name for input_pose in pose.get_all_input_poses()
            # ]

            # TODO figure out what I'm doing wrong here!
            targets_deltas = []

            for input_pose in pose.get_all_input_poses():
                target = input_pose.name

                if target in correctives_dict:
                    target_points = mhMayaUtils.get_points(correctives_dict[target], as_numpy=True)
                    target_delta = target_points - orig_points
                else:
                    target_delta = mhBlendshape.get_target_delta(bs_node, target, as_numpy=True)

                targets_deltas.append(target_delta)

            src_delta = numpy.sum(targets_deltas, axis=0)

            # points = orig_points + delta - src_delta
            points -= src_delta

            mhMayaUtils.set_points(inverted, points)

    # apply correctives
    LOG.info("applying correctives")

    for pose, target_index, ib_index, ib_value, inverted in correctives:
        if rebuild:
            # apply corrective as blendshape
            target_mesh, target_bs_node = mhBlendshape.rebuild_target(
                bs_node, target_index, parent=target_group, create_blendshape=True, inbetween_value=ib_value
            )

            mhBlendshape.append_blendshape_targets(
                target_bs_node, target_mesh, inverted, default_weight=1.0
            )

        else:
            # apply corrective delta directly
            # TODO test!
            inverted_points = mhMayaUtils.get_points(inverted, as_numpy=True)
            delta = inverted_points - orig_points
            mhBlendshape.set_target_delta(bs_node, target_index, delta, in_between=ib_index)

    # complete process
    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # reconnect joints
    LOG.info("reconnecting joints and targets")

    for attr, cons in joint_cons.items():
        cmds.connectAttr(cons, attr)

    for attr, cons in target_cons.items():
        cmds.connectAttr(cons, attr)

    # transfer skin weights
    # TODO

    # return
    LOG.info("Done")

    return True
