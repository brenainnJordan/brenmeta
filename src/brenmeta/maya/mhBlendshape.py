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

"""Blendshape utilities and objects that utilize OpenMaya

Maya blendshape docs:
https://help.autodesk.com/cloudhelp/2019/ENU/Maya-Tech-Docs/CommandsPython/blendShape.html

"""

import numpy

from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds
from maya import mel

from brenmeta.core import mhCore
from brenmeta.maya import mhMayaUtils

LOG = mhCore.get_basic_logger(__name__)


def find_mesh_blendshape_nodes(mesh):
    """
    We're not able to use the blendShape command to get the node name,
    so we need to find all blendShape nodes that influence the given mesh.
    """
    bs_nodes = cmds.ls(type="blendShape")

    if cmds.nodeType(mesh) == "mesh":
        mesh_transform = cmds.listRelatives(mesh, parent=True)[0]
    else:
        mesh_transform = mesh
        mesh = cmds.listRelatives(mesh, type="mesh")[0]

    matching_bs_nodes = []

    for bs_node in bs_nodes:
        meshes = cmds.blendShape(bs_node, query=True, geometry=True)
        if mesh in meshes or mesh_transform in meshes:
            matching_bs_nodes.append(bs_node)

    return matching_bs_nodes


def get_m_mesh(bs_node, index=0):
    bs_m_object = mhMayaUtils.parse_m_object(
        bs_node,
        # api_type=OpenMayaAnim.MFnGeometryFilter.type()
    )

    bs_fn = OpenMayaAnim.MFnGeometryFilter(bs_m_object)

    mesh_object = bs_fn.getOutputGeometry()[index]

    return mesh_object


def get_blendshape_weight_aliases(bs_node, as_dict=False):

    weight_indices = cmds.getAttr("{}.weight".format(bs_node), multiIndices=True)

    if as_dict:
        aliases = {}

        for i in weight_indices:
            alias = cmds.aliasAttr("{}.weight[{}]".format(bs_node, i), query=True)
            aliases[i] = alias

    else:
        aliases = []

        for i in weight_indices:
            alias = cmds.aliasAttr("{}.weight[{}]".format(bs_node, i), query=True)
            aliases.append(alias)

    return aliases


def get_blendshape_weight_alias(bs_node, target_index):
    alias = cmds.aliasAttr(
        "{}.weight[{}]".format(bs_node, target_index), query=True
    )

    return alias


def get_blendshape_target_index(bs_node, target_name):
    # aliases = get_blendshape_weight_aliases(bs_node)
    weight_indices = cmds.getAttr("{}.weight".format(bs_node), multiIndices=True)

    for i in weight_indices:
        alias = cmds.aliasAttr("{}.weight[{}]".format(bs_node, i), query=True)
        if target_name == alias:
            return i

    return None


def parse_target_arg(bs_node, target):
    if isinstance(target, str):
        target_index = get_blendshape_target_index(bs_node, target)
    else:
        # TODO check
        target_index = target
        target = get_blendshape_weight_alias(bs_node, target_index)

    return target, target_index


def is_combo(bs_node, target):
    if isinstance(target, int):
        target_attr = "{}.w[{}]".format(bs_node, target)
    else:
        target_attr = "{}.{}".format(bs_node, target)

    cons = cmds.listConnections(
        target_attr,
        source=True,
        destination=False,
        type="combinationShape"
    )

    if cons:
        return True
    else:
        return False


def get_combo_targets(bs_node, combo):
    if isinstance(combo, int):
        target_attr = "{}.w[{}]".format(bs_node, combo)
    else:
        target_attr = "{}.{}".format(bs_node, combo)

    combo_input = cmds.listConnections(
        target_attr,
        source=True,
        destination=False,
        type="combinationShape"
    )

    if not combo_input:
        # TODO raise?
        return None

    combo_node = combo_input[0]

    # get input targets
    combo_inputs = cmds.listConnections(
        "{}.inputWeight".format(combo_node),
        source=True,
        destination=False,
        plugs=True
    )

    combo_targets = [i.split(".")[1] for i in combo_inputs]

    return combo_targets


def append_blendshape_targets(bs_node, base_mesh, target, default_weight=0.0):
    """
    """
    target_index = cmds.blendShape(
        bs_node, query=True, weightCount=True
    )

    cmds.blendShape(
        bs_node, edit=True, target=(base_mesh, target_index, target, 1.0)
    )

    if default_weight:
        cmds.setAttr(
            "{}.w[{}]".format(bs_node, target_index),
            default_weight
        )

    return target_index


def add_in_between_target(bs_node, base_mesh, target, in_between_target, in_between_value):
    target_index = get_blendshape_target_index(bs_node, target)

    cmds.blendShape(
        bs_node,
        edit=True,
        target=(base_mesh, target_index, in_between_target, in_between_value)
    )

    return True


def create_empty_target(base_mesh, bs_node, name, default=0.0):
    """Python version of approach taken by maya when clicking 'add target'
    It's a bit dirty
    # TODO find a way of adding an empty target without duplicating the mesh
    """
    dummy_target = cmds.duplicate(base_mesh)[0]

    weight_indices = cmds.getAttr("{}.weight".format(bs_node), multiIndices=True)

    if weight_indices:
        index = max(weight_indices) + 1
    else:
        index = 0

    cmds.blendShape(
        bs_node,
        edit=True,
        target=(base_mesh, index, dummy_target, 1),
        weight=(index, 1)
    )

    cmds.dgdirty("{}.weight".format(bs_node))
    cmds.dgdirty("{}.weight[{}]".format(bs_node, index))

    weight_indices = cmds.getAttr("{}.weight".format(bs_node), multiIndices=True)
    cmds.refresh()

    # yes we could rename the duplicate mesh instead of doing an aliasAttr
    # but we want to remove the need for a duplicate mesh so makes sense to do it like this
    cmds.aliasAttr(name, "{}.weight[{}]".format(bs_node, index))

    cmds.delete(dummy_target)

    # reset delta
    cmds.blendShape(
        bs_node,
        edit=True,
        resetTargetDelta=[0, index]
    )

    # set default
    cmds.setAttr(
        "{}.{}".format(bs_node, name), default
    )

    return index


class BlendshapeTargetPlugs(object):
    """
    """

    def __init__(self, bs_node, target, in_between=None):

        self.in_between = in_between

        self.bs_m_object = mhMayaUtils.parse_m_object(
            bs_node,
            # api_type=OpenMayaAnim.MFnGeometryFilter.type()
        )

        self.bs_fn = OpenMayaAnim.MFnGeometryFilter(self.bs_m_object)

        if isinstance(target, str):
            self.target_alias = target
            self.target = get_blendshape_target_index(self.bs_fn.name(), target)
        else:
            self.target_alias = get_blendshape_weight_alias(self.bs_fn.name(), target)
            self.target = target

        self.mesh_object = self.bs_fn.getOutputGeometry()[0]

        geo_index = self.bs_fn.indexForOutputShape(self.mesh_object)

        # get plugs

        self.input_target = self.bs_fn.findPlug('inputTarget', False)

        self.input_target_indexed = self.input_target.elementByLogicalIndex(geo_index)

        self.input_target_group = self.input_target_indexed.child(0)

        self.input_target_group_indexed = self.input_target_group.elementByLogicalIndex(self.target)

        self.input_target_item = self.input_target_group_indexed.child(0)

        # note that a reference isn't kept to this as it can change
        item_indices = self.get_item_indices()

        if item_indices:
            if self.in_between is not None:
                if self.in_between < 5000:
                    in_between_index = item_indices[self.in_between]
                else:
                    in_between_index = self.in_between

                self.input_target_item_indexed = self.input_target_item.elementByLogicalIndex(
                    in_between_index
                )

            else:
                # elementByLogicalIndex
                self.input_target_item_indexed = self.input_target_item.elementByLogicalIndex(
                    item_indices[-1]
                )
        else:
            LOG.info("WARNING target has no existing input items: {} - {}".format(self.target, self.target_alias))

            self.input_target_item_indexed = self.input_target_item.elementByLogicalIndex(
                6000
            )

        self.input_geom = self.input_target_item_indexed.child(0)

        if False:
            # TODO
            # if it has an incoming mesh connection
            data_m_object = input_geom_target_plug.asMObject()
            # mesh_data = OpenMaya.MFnMeshData(data_m_object)

            data_mfn = OpenMaya.MFnMesh(data_m_object)

            test = data_mfn.getPoints()
            LOG.info(len(test))

        # this is basically our optimized point delta data
        # we only get back points that actually have a delta
        # then we can get the corresponding components
        self.points = self.input_target_item_indexed.child(3)

        # this is the corresponding components to our optimized points data
        self.components = self.input_target_item_indexed.child(4)

    def get_item_indices(self):
        return self.input_target_item.getExistingArrayAttributeIndices()

    def get_data(self, verbose=True):
        """get point and component data

        this is basically our optimized point delta data
        we only get back points that actually have a delta
        then we can get the corresponding components
        TODO catch when this returns None in other utils
        """

        if self.points.isDefaultValue():
            if verbose:
                LOG.info("# WARNING # input_components_target_plug isDefaultValue: {}".format(self.target_alias))
            point_data = None
        else:
            point_data_m_object = self.points.asMObject()
            point_data = OpenMaya.MFnPointArrayData(point_data_m_object)

        # get components
        if self.components.isDefaultValue():
            if verbose:
                LOG.info("# WARNING # input_components_target_plug isDefaultValue: {}".format(self.target_alias))
            component_list = None
        else:
            components_data_m_object = self.components.asMObject()
            component_list = OpenMaya.MFnComponentListData(components_data_m_object)

        return point_data, component_list

    def get_inbetween_indices(self):
        return list(self.get_item_indices())[:-1]

    def get_inbetween_values(self):
        indices = self.get_inbetween_indices()
        values = [(i - 5000) / 1000.0 for i in indices]
        return values, indices



def get_blendshape_target_data(bs_node, target, in_between=None):
    """TODO test more than one inbetween
    """

    target_plugs = BlendshapeTargetPlugs(bs_node, target, in_between=in_between)

    # get point data
    # this is basically our optimized point delta data
    # we only get back points that actually have a delta
    # then we can get the corresponding components
    point_data_m_object = target_plugs.points.asMObject()
    point_data = OpenMaya.MFnPointArrayData(point_data_m_object)

    # get components
    if target_plugs.components.isDefaultValue():
        LOG.info("# WARNING # input_components_target_plug isDefaultValue")
        component_list = None
    else:
        components_data_m_object = target_plugs.components.asMObject()
        component_list = OpenMaya.MFnComponentListData(components_data_m_object)

    return point_data, component_list


def get_target_delta(bs_node, target, in_between=None, as_numpy=False):
    # get point count
    m_mesh = get_m_mesh(bs_node)
    mesh_fn = OpenMaya.MFnMesh(m_mesh)
    point_count = mesh_fn.numVertices

    # get data
    plugs = BlendshapeTargetPlugs(bs_node, target, in_between=in_between)

    point_data, component_list = plugs.get_data()

    if as_numpy:
        delta = numpy.tile([0.0, 0.0, 0.0], (point_count, 1))

        if point_data:
            point_ids = mhMayaUtils.get_all_component_list_elements(component_list)
            delta[point_ids] = numpy.array(point_data)[:, :-1]

        return delta
    else:

        delta = OpenMaya.MPointArray(point_count, OpenMaya.MPoint())

        if point_data:
            point_ids = mhMayaUtils.get_all_component_list_elements(component_list)
            for point_id, point in zip(point_ids, point_data):
                delta[point_id] = point

        return delta


def get_summed_deltas(bs_node, targets):
    """TODO in-betweens
    """
    deltas = [
        get_target_delta(bs_node, target, as_numpy=True) for target in targets
    ]

    if len(targets) == 1:
        return deltas[0]
    else:
        deltas = [delta for delta in deltas if delta is not None]
        return numpy.sum(deltas, axis=0)


def get_summed_combo_delta(bs_node, target):
    delta = get_target_delta(bs_node, target, as_numpy=True)

    if delta is None:
        m_mesh = get_m_mesh(bs_node)
        mesh_fn = OpenMaya.MFnMesh(m_mesh)
        point_count = mesh_fn.numVertices

        delta = numpy.tile([0.0, 0.0, 0.0], (point_count, 1))

    if is_combo(bs_node, target):
        combo_targets = get_combo_targets(bs_node, target)

        for combo_target in combo_targets:
            combo_delta = get_target_delta(bs_node, combo_target, as_numpy=True)

            if combo_delta is not None:
                delta += combo_delta

    return delta


def set_target_delta(bs_node, target, delta, in_between=None, optimise=False, threshold=0.000000001):
    # get plugs
    target_plugs = BlendshapeTargetPlugs(bs_node, target, in_between=in_between)

    # reset target data
    point_data = OpenMaya.MFnPointArrayData()
    point_data.create()

    target_plugs.points.setMObject(point_data.object())
    target_plugs.components.setMObject(OpenMaya.MObject())

    # delta_count = len(delta)

    # optimise
    if optimise:
        if not isinstance(delta, numpy.ndarray):
            delta = numpy.array(delta)

        # get vertex ids and delta where the sum of the delta is greater than zero
        vertex_ids = numpy.argwhere(numpy.abs(delta).sum(axis=1) > 0.0).flatten()
        delta = delta[vertex_ids]
    else:
        vertex_ids = list(range(len(delta)))

    # print("count: ", len(vertex_ids), delta_count)

    # create point data
    if isinstance(delta, numpy.ndarray):
        delta = OpenMaya.MPointArray([
            OpenMaya.MPoint(point) for point in delta
        ])

    point_data = OpenMaya.MFnPointArrayData()
    point_data.create(delta)

    # create component data
    component_list = OpenMaya.MFnComponentListData()
    component_list.create()

    component = OpenMaya.MFnSingleIndexedComponent()

    component.create(OpenMaya.MFn.kMeshVertComponent)

    elements = OpenMaya.MIntArray(vertex_ids)

    component.addElements(elements)

    component_list.add(component.object())

    # set point data
    target_plugs.points.setMObject(point_data.object())

    # set components
    target_plugs.components.setMObject(component_list.object())

    return True


def combine_deltas(bs_node, src_targets, target_weights, dst_target):
    """Sum deltas of given src_targets after multiplying by target_weights and set as dst_target

from brenmy.deformers import bmBlendshape

bmBlendshape.combine_deltas(
    "CloakSubD_BS",
    ["Lf_Shoulder_y_neg_90", "Lf_Shoulder_z_pos_90"],
    [-0.5, -0.5],
    #[0.0, 0.0],
    "Lf_Shoulder_y_neg_90_z_pos_90"
)

    """
    m_mesh = get_m_mesh(bs_node)

    mesh_fn = OpenMaya.MFnMesh(m_mesh)
    point_count = mesh_fn.numVertices

    delta = numpy.array([[0.0, 0.0, 0.0] for _ in range(point_count)])

    for src_target, target_weight in zip(src_targets, target_weights):
        target_delta = get_target_delta(bs_node, src_target, as_numpy=True)

        if target_delta is None:
            continue

        target_delta *= target_weight
        delta += target_delta

    set_target_delta(bs_node, dst_target, delta)

    return True


def un_combine_deltas(bs_node, src_targets, target_weights, dst_target, optimise=True, in_between=None):
    """Subtract deltas of src_targets after multiplying by target_weights and set as dst_target
    """
    m_mesh = get_m_mesh(bs_node)

    mesh_fn = OpenMaya.MFnMesh(m_mesh)
    point_count = mesh_fn.numVertices

    if in_between is not None:
        # TODO validate that all targets have the same in_between index
        pass

    delta = get_target_delta(bs_node, dst_target, as_numpy=True, in_between=in_between)

    if delta is None:
        # TODO warning
        return

    for src_target, target_weight in zip(src_targets, target_weights):
        target_delta = get_target_delta(bs_node, src_target, as_numpy=True, in_between=in_between)

        if target_delta is None:
            continue

        target_delta *= target_weight
        delta -= target_delta

    set_target_delta(bs_node, dst_target, delta, optimise=optimise, in_between=in_between)

    return True


# def apply_sculpt_delta(bs_node, target, sculpt_delta, rebuild=True, group=None, verbose=True):
#     target_plugs = BlendshapeTargetPlugs(bs_node, target)
#     inbetween_values, inbetween_indices = target_plugs.get_inbetween_values()
#     target_index = target_plugs.target
#
#     if rebuild:
#         # rebuild target and apply split sculpt as a blendshape
#         rebuild_result = cmds.sculptTarget(bs_node, edit=True, regenerate=True, target=target_index)
#
#         if rebuild_result:
#             target_mesh = rebuild_result[0]
#
#             if group:
#                 cmds.parent(target_mesh, group)
#
#             target_bs_node = cmds.deformer(
#                 target_mesh, type="blendShape", name="{}_blendShape".format(target_mesh)
#             )[0]
#
#             create_empty_target(
#                 target_mesh, target_bs_node, "sculpt", default=1.0
#             )
#         else:
#             # target already rebuilt
#             target_mesh = get_blendshape_weight_alias(bs_node, target_index)
#             target_bs_node = "{}_blendShape".format(target_mesh)
#
#         set_target_delta(target_bs_node, 0, sculpt_delta)
#
#     else:
#         # apply split delta directly
#         delta += sculpt_delta
#         set_target_delta(bs_node, target_index, delta)
#
#     # distribute delta to in-betweens
#     for in_between, inbetween_value in enumerate(inbetween_values):
#         if verbose:
#             LOG.info("   in-between: {}".format(inbetween_value))
#
#         ib_target_mesh = "{}_{}".format(
#             target_plugs.target_alias,
#             str(inbetween_value).replace(".", "_")
#         )
#
#         inbetween_delta = sculpt_delta * inbetween_value
#
#         if rebuild:
#             # rebuild target and apply split sculpt as a blendshape
#             rebuild_result = cmds.sculptTarget(
#                 bs_node, edit=True, regenerate=True, target=target_index, inbetweenWeight=inbetween_value
#             )
#
#             target_bs_node = "{}_blendShape".format(ib_target_mesh)
#
#             if rebuild_result:
#                 ib_target_mesh = cmds.rename(rebuild_result[0], ib_target_mesh)
#
#                 if group:
#                     cmds.parent(ib_target_mesh, group)
#
#                 target_bs_node = cmds.deformer(
#                     ib_target_mesh, type="blendShape", name="{}_blendShape".format(ib_target_mesh)
#                 )[0]
#
#                 create_empty_target(
#                     ib_target_mesh, target_bs_node, "sculpt", default=1.0
#                 )
#
#             set_target_delta(target_bs_node, 0, inbetween_delta)
#
#         else:
#             # apply split delta directly
#             set_target_delta(bs_node, target_index, delta + inbetween_delta, in_between=in_between)
#
#     return True


def apply_sculpt(bs_node, sculpt, sculpt_prefix, rebuild=True, group=None, verbose=True):

    target = sculpt[len(sculpt_prefix):]

    target_plugs = BlendshapeTargetPlugs(bs_node, target)
    inbetween_values, inbetween_indices = target_plugs.get_inbetween_values()
    target_index = target_plugs.target

    delta = get_target_delta(bs_node, target, as_numpy=True)

    base_mesh = mhMayaUtils.get_orig_mesh(bs_node)
    base_points = mhMayaUtils.get_points(base_mesh, as_positions=True)
    sculpt_points = mhMayaUtils.get_points(sculpt, as_positions=True)

    sculpt_points = numpy.array(sculpt_points)
    base_points = numpy.array(base_points)

    sculpt_delta = sculpt_points - base_points - delta

    # apply_sculpt_delta(bs_node, target, sculpt_delta, rebuild=rebuild, group=group)


    if rebuild:
        # rebuild target and apply split sculpt as a blendshape
        rebuild_result = cmds.sculptTarget(bs_node, edit=True, regenerate=True, target=target_index)

        if rebuild_result:
            target_mesh = rebuild_result[0]

            if group:
                cmds.parent(target_mesh, group)

            target_bs_node = cmds.deformer(
                target_mesh, type="blendShape", name="{}_blendShape".format(target_mesh)
            )[0]

            create_empty_target(
                target_mesh, target_bs_node, "sculpt", default=1.0
            )
        else:
            # target already rebuilt
            target_mesh = get_blendshape_weight_alias(bs_node, target_index)
            target_bs_node = "{}_blendShape".format(target_mesh)

        set_target_delta(target_bs_node, 0, sculpt_delta)

    else:
        # apply split delta directly
        delta += sculpt_delta
        set_target_delta(bs_node, target_index, delta)

    # distribute delta to in-betweens
    for in_between, inbetween_value in enumerate(inbetween_values):
        if verbose:
            LOG.info("   in-between: {}".format(inbetween_value))

        ib_target_mesh = "{}_{}".format(
            target_plugs.target_alias,
            str(inbetween_value).replace(".", "_")
        )

        ib_sculpt = "{}{}".format(sculpt_prefix, ib_target_mesh)

        if cmds.objExists(ib_sculpt):
            # use in between sculpt delta
            LOG.info("    in-between sculpt: {}".format(ib_sculpt))

            ib_sculpt_points = mhMayaUtils.get_points(ib_sculpt, as_positions=True)
            ib_sculpt_points = numpy.array(ib_sculpt_points)

            ib_delta = get_target_delta(bs_node, target, as_numpy=True, in_between=in_between)

            inbetween_delta = ib_sculpt_points - base_points - ib_delta

        else:
            # distribute main delta to in between
            inbetween_delta = sculpt_delta * inbetween_value

        if rebuild:
            # rebuild target and apply split sculpt as a blendshape
            rebuild_result = cmds.sculptTarget(
                bs_node, edit=True, regenerate=True, target=target_index, inbetweenWeight=inbetween_value
            )

            target_bs_node = "{}_blendShape".format(ib_target_mesh)

            if rebuild_result:
                ib_target_mesh = cmds.rename(rebuild_result[0], ib_target_mesh)

                if group:
                    cmds.parent(ib_target_mesh, group)

                target_bs_node = cmds.deformer(
                    ib_target_mesh, type="blendShape", name="{}_blendShape".format(ib_target_mesh)
                )[0]

                create_empty_target(
                    ib_target_mesh, target_bs_node, "sculpt", default=1.0
                )

            set_target_delta(target_bs_node, 0, inbetween_delta)

        else:
            # apply split delta directly
            set_target_delta(bs_node, target_index, delta + inbetween_delta, in_between=in_between)

    return True


def sort_sculpts(sculpts):
    """sort by combo order"""
    sorted_sculpts = {}

    for sculpt in sculpts:
        target_tokens = sculpt.split("_")
        token_count = len(target_tokens)

        if token_count in sorted_sculpts:
            sorted_sculpts[token_count].append(sculpt)
        else:
            sorted_sculpts[token_count] = [sculpt]

    return sorted_sculpts


def apply_sculpts(bs_node, sculpts, sculpt_prefix, rebuild=True):
    group = "targets"

    if not cmds.objExists(group):
        cmds.createNode("transform", name=group)

    sorted_sculpts = sort_sculpts(sculpts)

    for token_count in sorted(sorted_sculpts.keys()):
        for sculpt in sorted_sculpts[token_count]:
            target = sculpt[len(sculpt_prefix):]

            if get_blendshape_target_index(bs_node, target) is None:
                LOG.warning("Target not found: {} -> {}.{}".format(sculpt, bs_node, target))
                continue

            LOG.info("Applying sculpt: {} -> {}.{}".format(sculpt, bs_node, target))

            apply_sculpt(
                bs_node,
                sculpt,
                sculpt_prefix,
                rebuild=rebuild,
                group=group
            )

    return True
