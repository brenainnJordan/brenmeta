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
        self.file_path = None

        self.mesh_blendshapes = None
        self.shapes = None
        self.in_betweens = None
        self.combos = None
        self.pose_joints = None
        self.keep_joints = None
        self.delete = None
        self.root_joints = None
        self.readers = None
        self.pose_deltas = None

    @property
    def meshes(self):
        return [a for a, b in self.mesh_blendshapes]

    @property
    def blendshape_nodes(self):
        return [b for a, b in self.mesh_blendshapes]

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

        config.file_path = file_path

        config.mesh_blendshapes = data["mesh_blendshapes"]
        # config.shapes = data["shapes"]
        config.in_betweens = data["in_betweens"]
        config.pose_joints = data["pose_joints"]
        config.keep_joints = data["keep_joints"]
        config.delete = data["delete"]
        config.root_joints = data["root_joints"]

        if "readers" in data:
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

        if "pose_deltas" in data:
            config.pose_deltas = data["pose_deltas"]

        return config

    def update_pose_manager(self, pose_manager):
        LOG.info(
            "Adding additional shapes and combos from bake config: {}".format(self.file_path)
        )

        # create additional poses
        if self.shapes:
            LOG.info("Adding additional poses...")

            new_poses = pose_manager.add_additional_poses(self.shapes, pose_deltas=self.pose_deltas)

        # create additional combos
        if self.combos:
            LOG.info("Adding additional combo poses...")

            new_combos = pose_manager.add_additional_combo_poses(self.combos)

            pose_manager.update_input_combo_poses()

        # add additional blendshape nodes
        if self.mesh_blendshapes:
            LOG.info("Adding additional meshes and blendshapes...")
            pose_manager.mesh_blendshapes += self.mesh_blendshapes

        return new_poses, new_combos


def delete_redundant_joints(keep_joints, pose_joints):
    joints = cmds.ls(type="joint")
    joints = [i for i in joints if i not in keep_joints + pose_joints]
    cmds.delete(joints)


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
        core_poses, combo_poses, expressions_node, additional_shapes=None, use_combo_network=True, reader_configs=None
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
                    max=1.0,
                    keyable=True
                )

            expressions.append(shape_name)

    # create driver mapping for non-combo poses
    driver_mapping = {}

    for pose_index, pose in enumerate(core_poses):
        # if pose_index in combo_poses or pose.name is None:
        #     continue
        if pose.name is None:
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

    for combo_pose in combo_poses:#.values():
        combo_node = cmds.createNode(
            "combinationShape",
            name="{}_combinationShape".format(combo_pose.pose.name)
        )

        combo_valid = True

        for index, pose in enumerate(combo_pose.input_poses):
            # weight = combo_pose.input_weights[index]

            if pose.name not in driver_mapping:
                combo_valid = False
                break

            output_attr = driver_mapping[pose.name]

            cmds.connectAttr(
                output_attr,
                "{}.inputWeight[{}]".format(combo_node, index)
            )

        if not combo_valid:
            LOG.warning("combo not valid: {}".format(combo_pose.pose.name))
            cmds.delete(combo_node)
            continue

        if use_combo_network:
            # map via combo network node
            cmds.addAttr(
                combo_network_node, longName=combo_pose.pose.name, defaultValue=0.0
            )

            cmds.connectAttr(
                "{}.outputWeight".format(combo_node),
                "{}.{}".format(combo_network_node, combo_pose.pose.name)
            )

            driver_mapping[combo_pose.pose.name] = "{}.{}".format(combo_network_node, combo_pose.pose.name)
        else:
            # map to combo node directly
            driver_mapping[combo_pose.pose.name] = "{}.outputWeight".format(combo_node)

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


def get_attr_pose_data(pose_manager, pose_joints=None):
    """Build a dict where key is every attr for all joints we want to still have driven
    and value is all poses that drive that attr
    """
    attr_pose_data = {}

    if pose_joints:
        # find only poses that affect given joints
        for joint in pose_joints:
            if not cmds.objExists(joint):
                LOG.warning("Joint not found: {}".format(joint))
                continue

            for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
                joint_attr = "{}.{}".format(joint, attr)

                joint_poses = []

                for pose in pose_manager.poses:
                    if isinstance(pose, mhCore.ComboPose):
                        pose = pose.pose

                    if joint_attr in pose.deltas:
                        joint_poses.append(pose)

                attr_pose_data[joint_attr] = joint_poses
    else:
        # remap all poses to attrs
        for pose in pose_manager.poses:
            if isinstance(pose, mhCore.ComboPose):
                pose = pose.pose

            for attr, value in pose.deltas.items():
                if attr in attr_pose_data:
                    attr_pose_data[attr].append(pose)
                else:
                    attr_pose_data[attr] = [pose]

    return attr_pose_data


def create_joint_poses(pose_manager, driver_mapping, pose_joints=None):
    attr_pose_data = get_attr_pose_data(pose_manager, pose_joints=pose_joints)

    # loop through driven attrs
    for attr, attr_poses in attr_pose_data.items():
        if not attr_poses:
            continue

        network_node = cmds.createNode(
            "network",
            name="{}_poses".format(attr.replace(".", "_"))
        )

        default = pose_manager.attr_defaults[attr]

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

        parsed_pose_names = []

        for pose in attr_poses:
            if pose.deltas[attr] == 0.0:
                continue

            # avoid duplicate named poses
            if pose.name in parsed_pose_names:
                continue
            else:
                parsed_pose_names.append(pose.name)

            if not pose.name:
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

def create_sdk(node, attr, driver, driver_value, driven_value):
    old_blends = cmds.ls(type="blendWeighted")

    cmds.setDrivenKeyframe(
        node,
        attribute=attr,
        currentDriver=driver,
        driverValue=driver_value,
        value=driven_value,
        inTangentType="linear",
        outTangentType="linear",
    )

    updated_blends = cmds.ls(type="blendWeighted")
    new_blends = [i for i in updated_blends if i not in old_blends]

    if new_blends:
        cmds.rename(new_blends[0], "{}_{}_SDK_blendWeighted".format(node, attr))

    return True


def create_joint_poses_sdk(pose_manager, driver_mapping, pose_joints=None):
    attr_pose_data = get_attr_pose_data(pose_manager, pose_joints=pose_joints)

    default_network_node = cmds.createNode("network", name="sdkDefault_network")

    cmds.addAttr(default_network_node, longName="default", defaultValue=1.0)

    # loop through driven attrs
    for joint_attr, attr_poses in attr_pose_data.items():
        if not attr_poses:
            continue

        parsed_pose_names = []

        joint, attr = joint_attr.split(".")

        # sdk for attr default value
        create_sdk(
            joint,
            attr,
            "{}.default".format(default_network_node),
            0.0,
            0.0
        )

        create_sdk(
            joint,
            attr,
            "{}.default".format(default_network_node),
            1.0,
            pose_manager.attr_defaults[joint_attr]
        )

        for pose in attr_poses:
            if pose.deltas[joint_attr] == 0.0:
                continue

            # avoid duplicate named poses
            if pose.name in parsed_pose_names:
                continue
            else:
                parsed_pose_names.append(pose.name)

            if not pose.name:
                continue

            if pose.name not in driver_mapping:
                LOG.warning("no expression for {}".format(pose.name))
                continue

            create_sdk(
                joint,
                attr,
                driver_mapping[pose.name],
                0.0,
                0.0
            )

            create_sdk(
                joint,
                attr,
                driver_mapping[pose.name],
                1.0,
                pose.deltas[joint_attr]
            )

    return True


def bake_shapes_from_poses(mesh_blendshapes, pose_manager, in_betweens, detailed_verbose=True, skip_empty=False):
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

    # pose_names = []

    # start progress bar
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Baking shapes...',
        maxValue=len(pose_manager.poses)
    )

    for pose_index, pose in enumerate(pose_manager.poses):
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        # pose rig
        # if pose_index in pose_manager.combo_poses:
        #     combo_pose = pose_manager.combo_poses[pose_index]
        #     combo_pose.pose_joints(summed=True)
        #     pose_name = combo_pose.pose.name
        #     pose = combo_pose
        # else:
        #     pose.pose_joints()
        #     pose_name = pose.name
        #     pose_names.append(pose_name)

        if isinstance(pose, mhCore.ComboPose):
            pose.pose_joints(summed=True)
            pose_name = pose.pose.name
        else:
            pose.pose_joints()
            pose_name = pose.name
            # pose_names.append(pose_name)

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

        pose_manager.reset_joints()

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

                pose_manager.reset_joints()

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    return base_meshes, bs_nodes, target_groups


def calculate_combo_deltas(
        bs_node, combo_poses, in_betweens, detailed_verbose=True, optimise=True,
        calculate_inputs=True
):
    """
    Note we always use the pose names to find the targets instead of the pose index
    as the target index may not match the corresponding pose
    (for example if targets have been added or removed)

    In the case that targets have been renamed, and the pose name no longer matches,
    it's better to fail and stop the process, than continue and have unexpected results.

    """
    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    all_targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Calculating Combo deltas ({})...'.format(bs_node),
        maxValue=len(combo_poses)
    )

    for combo_pose in combo_poses:
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        # check if this target was skipped
        if combo_pose.pose.name not in all_targets:
            continue

        src_targets = [
            pose.name for pose in combo_pose.input_poses if pose.name in all_targets
        ]

        if not src_targets:
            LOG.warning("No source targets found: {}".format(combo_pose.pose.name))
            continue

        if detailed_verbose:
            LOG.info("    {}".format(combo_pose.pose.name))

            src_target_names = [
                pose.name for pose in combo_pose.input_poses if pose.name in all_targets
            ]

            LOG.info("      - {}".format(src_target_names))

        weights = [1.0] * len(src_targets)

        mhBlendshape.un_combine_deltas(
            bs_node,
            src_targets,
            weights,
            combo_pose.pose.name,
            optimise=optimise,
        )

        if combo_pose.pose.name in in_betweens:
            in_between_count = in_betweens[combo_pose.pose.name]
            in_between_targets = []

            for ib_index in range(in_between_count):
                # uncombine in-between
                mhBlendshape.un_combine_deltas(
                    bs_node,
                    src_targets,
                    weights,
                    combo_pose.pose.name,
                    optimise=optimise,
                    in_between=ib_index
                )

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # subtract input combos
    if calculate_inputs:
        LOG.info("Calculating input Combo deltas ({}) ...".format(bs_node))

        # do this in order of least combos to most combos
        for combo_count in range(3, 10):
            for combo_pose in combo_poses:
                if len(combo_pose.input_poses) != combo_count:
                    continue

                if combo_pose.pose.name not in all_targets:
                    continue

                src_targets = [
                    pose.pose.name for pose in combo_pose.input_combos
                ]

                if not src_targets:
                    LOG.warning("No input combo poses found: {}".format(combo_pose.pose.name))
                    continue

                if detailed_verbose:
                    LOG.info("    {}".format(combo_pose.pose.name))
                    LOG.info("      - {}".format(src_targets))

                weights = [1.0] * len(src_targets)

                mhBlendshape.un_combine_deltas(
                    bs_node,
                    src_targets,
                    weights,
                    combo_pose.pose.name,
                    optimise=optimise,
                )

    return True


def bake_rig(
        pose_manager,
        bake_config_file,
        bake_shapes=True,
        calculate_combos=True,
        connect_shapes=True,
        connect_joints=True,
        optimise=True,
        delete_targets=True,
        delete_unused=True,
        expressions_node="CTRL_expressions",
        use_combo_network=False,
        detailed_verbose=False,
        use_sdks=False,
):
    """
    """
    # load config
    bake_config = BakeConfig.load(bake_config_file)
    bake_config.update_pose_manager(pose_manager)

    meshes = [mesh for mesh, bs_node in bake_config.mesh_blendshapes]
    bs_nodes = [bs_node for mesh, bs_node in bake_config.mesh_blendshapes]

    # break joint connections
    if bake_shapes or connect_joints:
        break_joint_connections(bake_config.root_joints)

    # create base mesh and blendshape node
    if bake_shapes:
        LOG.info("Disconnecting joints...")

        LOG.info("Baking shapes...")

        base_meshes, bs_nodes, target_groups = bake_shapes_from_poses(
            bake_config.mesh_blendshapes,
            pose_manager,
            bake_config.in_betweens,
            detailed_verbose=detailed_verbose
        )

        # delete original meshes
        cmds.delete(meshes)

        # rename baked meshes
        for base_mesh, mesh in zip(base_meshes, meshes):
            cmds.rename(base_mesh, mesh)

        if delete_targets:
            cmds.refresh()
            cmds.delete(target_groups)
            cmds.refresh()

    # delete targets so we can edit the deltas
    if calculate_combos:
        # calculate combo blendshape deltas and subtract
        LOG.info("Calculating Combo deltas...")

        for bs_node in bs_nodes:
            LOG.info("  Blendshape node: {}".format(bs_node))

            calculate_combo_deltas(
                bs_node,
                pose_manager.combo_poses,
                bake_config.in_betweens,
                detailed_verbose=True,
                optimise=optimise
            )

    # create combo logic
    if connect_shapes or connect_joints:
        LOG.info("Creating driver logic...")

        driver_mapping = create_driver_logic(
            pose_manager.core_poses,
            pose_manager.combo_poses,
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

        if use_sdks:
            LOG.info("Using SDKs...")

            create_joint_poses_sdk(
                pose_manager,
                driver_mapping,
                pose_joints=bake_config.pose_joints
            )
        else:
            LOG.info("Using math nodes...")

            create_joint_poses(
                pose_manager,
                driver_mapping,
                pose_joints=bake_config.pose_joints
            )

    # cleanup
    if delete_unused:
        rl4_nodes = cmds.ls(type="embeddedNodeRL4")

        if rl4_nodes:
            cmds.delete(rl4_nodes)

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
                    try:
                        cmds.disconnectAttr(cons[0], target_attr)
                    except:
                        LOG.warning("failed to disconnect: {} -> {}".format(cons[0], target_attr))

    # disconnect joints and delete networks
    if disconnect_joints:
        if verbose:
            LOG.info("Disconnecting joints")

        redundant_nodes = cmds.ls("*_poses", type="network")
        cmds.delete(redundant_nodes)

        redundant_nodes = cmds.ls("*_SDK_blendWeighted", type="blendWeighted")
        cmds.delete(redundant_nodes)

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
        pose_manager,
        config_file_path,
        expressions_node="CTRL_expressions",
        reconnect_joints=True,
        baked_joints_only=True,
        reconnect_targets=True,
        use_combo_network=False,
        add_missing_targets=True,
        use_sdks=False
):
    """
    """
    # load config
    bake_config = BakeConfig.load(config_file_path)

    new_poses, new_combo_poses = bake_config.update_pose_manager(pose_manager)

    bs_nodes = [
        bs_node for mesh, bs_node in bake_config.mesh_blendshapes if cmds.objExists(bs_node)
    ]

    # create combo logic
    LOG.info("Creating driver logic...")

    driver_mapping = create_driver_logic(
        pose_manager.core_poses,
        pose_manager.combo_poses,
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
            new_shapes += [combo_pose.pose.name for combo_pose in new_combo_poses]

            for shape_name in new_shapes:
                if mhBlendshape.get_blendshape_target_index(bs_node, shape_name)[0] is not None:
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

    # reconnect joints
    if reconnect_joints and baked_joints_only:
        LOG.info("Reconnecting baked joints")

        if use_sdks:
            LOG.info("Using SDKs...")

            create_joint_poses_sdk(
                pose_manager,
                driver_mapping,
                pose_joints=bake_config.pose_joints
            )
        else:
            LOG.info("Using math nodes...")

            create_joint_poses(
                pose_manager,
                driver_mapping,
                pose_joints=bake_config.pose_joints
            )
    elif reconnect_joints:
        LOG.info("Reconnecting all joints")

        if use_sdks:
            LOG.info("Using SDKs...")

            create_joint_poses_sdk(
                pose_manager.poses,
                driver_mapping,
                pose_joints=None
            )
        else:
            LOG.info("Using math nodes...")

            create_joint_poses(
                pose_manager.poses,
                driver_mapping,
                pose_joints=None
            )

    return True


def extract_pose_correctives(
        pose_manager, bake_config_file, mesh, bs_node, skinned_mesh, cleanup=True
):
    """Extracts corrective shapes using given skinned mesh as reference.

    Targets will be replaced with corrective shapes,
    and skin weights will be transferred to mesh after extraction.

    Only poses that affect the skinned joint hierarchy will be processed.

    TODO option to extract all
    """
    # load config
    bake_config = BakeConfig.load(config_file_path)

    new_poses, new_combo_poses = bake_config.update_pose_manager(pose_manager)

    # check mesh and skinned mesh are different
    if mesh == skinned_mesh:
        raise mhCore.MHError("Mesh and Skinned Mesh cannot be the same")

    # check skin clusters
    existing_skin = mhMayaUtils.find_related_skin_cluster(mesh)

    if existing_skin:
        raise mhCore.MHError("SkinCluster found on mesh: {}".format(mesh))

    existing_skin = mhMayaUtils.find_related_skin_cluster(skinned_mesh)

    if not existing_skin:
        raise mhCore.MHError("No skinCluster found on mesh: {}".format(skinned_mesh))

    # get skinned joints
    skin_cluster = mhMayaUtils.find_related_skin_cluster(skinned_mesh)

    driven_joints = cmds.skinCluster(skin_cluster, query=True, influence=True)

    # get targets
    targets = mhBlendshape.get_blendshape_weight_aliases(bs_node)

    if len(targets) > len(poses):
        LOG.warning("There are more targets than poses: {} targets({}) {} poses".format(
            len(targets), bs_node, len(poses)
        ))

    # get points
    orig_mesh = mhMayaUtils.get_orig_mesh(bs_node, as_name=True)
    orig_points = mhMayaUtils.get_points(orig_mesh, as_numpy=True)

    # TODO check that mesh points match orig points!

    # get parent of joints
    driven_joints = set(driven_joints)

    for joint in list(driven_joints):
        parents = mhMayaUtils.get_all_parents(joint)
        parent_joints = cmds.ls(parents, type="joint")
        driven_joints.update(parent_joints)

    driven_joints = list(driven_joints)

    LOG.info("driven joints: {}".format(driven_joints))

    # temporarily disconnect all joints and targets in the scene
    LOG.info("disconnecting joints and targets")
    all_joints = cmds.ls(type="joint")
    joint_cons = mhMayaUtils.disconnect_transforms(all_joints)
    target_cons = mhMayaUtils.disconnect_attrs(bs_node, targets)

    # create groups
    sculpts_group = cmds.createNode("transform", name="sculpts_grp")
    correctives_group = cmds.createNode("transform", name="correctives_grp")

    # determine which poses affect driven joints
    LOG.info("Driver poses:")

    driver_poses = {}
    parsed_pose_names = []

    for i, pose in enumerate(poses):
        if pose.name not in targets:
            continue

        # skip duplicates
        if pose.name in parsed_pose_names:
            continue

        pose_name = pose.name
        relevant_shapes = [pose_name]
        parsed_pose_names.append(pose_name)

        if i in combo_poses:
            pose = combo_poses[i]

        if not pose.affects_joints(driven_joints):
            continue

        driver_poses[i] = pose

        LOG.info("  {}".format(pose))

    # extract "sculpts" from shapes
    LOG.info("Extracting sculpts...")

    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Extracting sculpts...',
        maxValue=len(driver_poses)
    )

    sculpts_dict = {}
    combo_poses_to_calculate = {}

    for i, pose in driver_poses.items():
        if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
            cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
            return False

        cmds.progressBar(gMainProgressBar, edit=True, step=1)

        if isinstance(pose, mhCore.ComboPose):
            pose_name = pose.pose.name

            relevant_shapes = [pose_name] + [
                input_pose.name for input_pose in pose.get_all_input_poses(include_combos=True)
                if input_pose.name in targets
            ]

            if len(relevant_shapes) > 1:
                combo_poses_to_calculate[i] = pose

        else:
            pose_name = pose.name
            relevant_shapes = [pose_name]

        # get data
        logical_index, target_index = mhBlendshape.get_blendshape_target_index(bs_node, pose_name)
        plugs = mhBlendshape.BlendshapeTargetPlugs(bs_node, target_index)
        ib_values, ib_indices = plugs.get_inbetween_values()

        # loop through full value and inbetween values
        values = [1.0] + ib_values

        sculpts_dict[pose_name] = {}

        for index, value in enumerate(values):
            LOG.info("extracting sculpt: {} at {}".format(pose_name, value))

            if value != 1.0:
                ib_value = value
                ib_index = index - 1
            else:
                ib_value = None
                ib_index = None

            # turn on shape(s)
            for shape in relevant_shapes:
                cmds.setAttr("{}.{}".format(bs_node, shape), value)

            # duplicate
            if ib_index is not None:
                sculpt = "{}_IB{}_sculpt".format(pose_name, ib_index)
            else:
                sculpt = "{}_sculpt".format(pose_name)

            cmds.duplicate(mesh, name=sculpt)

            cmds.parent(sculpt, sculpts_group)

            sculpts_dict[pose_name][value] = sculpt

            for shape in relevant_shapes:
                cmds.setAttr("{}.{}".format(bs_node, shape), 0.0)

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # reset deltas on all relevant targets
    LOG.info("Resetting deltas...")

    for pose in driver_poses.values():
        if isinstance(pose, mhCore.ComboPose):
            pose_name = pose.pose.name
        else:
            pose_name = pose.name

        logical_index, target_index = mhBlendshape.get_blendshape_target_index(bs_node, pose_name)

        cmds.blendShape(
            bs_node,
            edit=True,
            resetTargetDelta=[0, target_index],
        )

    # extract correctives
    LOG.info("Extracting correctives...")

    gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

    cmds.progressBar(
        gMainProgressBar,
        edit=True,
        beginProgress=True,
        isInterruptable=True,
        status='Extracting correctives...',
        maxValue=len(driver_poses)
    )

    correctives_dict = {}

    for combo_count in range(1, 10):
        for i, pose in driver_poses.items():
            if cmds.progressBar(gMainProgressBar, query=True, isCancelled=True):
                cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
                return False

            if isinstance(pose, mhCore.ComboPose):
                pose_name = pose.pose.name
            else:
                pose_name = pose.name

            if combo_count == 1:
                # primary only, skip combos
                if isinstance(pose, mhCore.ComboPose):
                    continue
            else:
                # combo only, skip primary
                if not isinstance(pose, mhCore.ComboPose):
                    continue

                if len(pose.input_poses) != combo_count:
                    continue

            cmds.progressBar(gMainProgressBar, edit=True, step=1)

            LOG.info("  {}".format(pose_name))

            # get data
            logical_index, target_index = mhBlendshape.get_blendshape_target_index(bs_node, pose_name)
            plugs = mhBlendshape.BlendshapeTargetPlugs(bs_node, target_index)
            ib_values, ib_indices = plugs.get_inbetween_values()

            # loop through full value and inbetween values
            values = [1.0] + ib_values

            correctives_dict[pose_name] = []

            for index, value in enumerate(values):
                LOG.info("extracting corrective: {} at {}".format(pose_name, value))

                if value != 1.0:
                    ib_value = value
                    ib_index = index - 1
                else:
                    ib_value = None
                    ib_index = None

                # pose joints and turn on input shapes
                pose.pose_joints(blend=value)

                # get sculpt
                sculpt = sculpts_dict[pose_name][value]

                # extract corrective
                corrective = cmds.invertShape(skinned_mesh, sculpt)

                if ib_index is not None:
                    corrective = cmds.rename(corrective, "{}_IB{}_corrective".format(pose_name, ib_index))
                else:
                    corrective = cmds.rename(corrective, "{}_corrective".format(pose_name))

                correctives_dict[pose_name].append((value, ib_index, corrective))

                cmds.parent(corrective, correctives_group)

                cmds.sets(corrective, edit=True, forceElement="initialShadingGroup")

                # reset joints and shapes
                pose.reset_joints()

    cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)

    # apply correctives
    LOG.info("applying correctives")

    for pose_name, corrective_data in correctives_dict.items():
        logical_index, target_index = mhBlendshape.get_blendshape_target_index(bs_node, pose_name)

        for value, ib_index, corrective in corrective_data:
            # apply corrective delta directly
            target_points = mhMayaUtils.get_points(corrective, as_numpy=True)
            delta = target_points - orig_points

            mhBlendshape.set_target_delta(
                bs_node,
                target_index,
                delta,
                in_between=ib_index
            )

    # calculate Combo deltas
    LOG.info("Calculating Combo deltas")

    calculate_combo_deltas(
        bs_node,
        combo_poses_to_calculate,
        bake_config.in_betweens,
        detailed_verbose=True,
        optimise=True,
        calculate_inputs=True
    )

    # reconnect joints
    LOG.info("reconnecting joints and targets")

    for attr, cons in joint_cons.items():
        cmds.connectAttr(cons, attr)

    for attr, cons in target_cons.items():
        cmds.connectAttr(cons, attr)

    # transfer skin weights
    LOG.info("Transferring skin weights")

    mhMayaUtils.transfer_skin(skinned_mesh, mesh)

    # cleanup
    if cleanup:
        cmds.delete(sculpts_group, correctives_group)

    # return
    LOG.info("Done")

    return True
