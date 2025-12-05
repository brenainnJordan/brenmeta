"""Blendshape utilities and objects that utilize OpenMaya

For utilities that only use maya commands see brenmy.utils.bmBlendshapeUtils

Maya blendshape docs:
https://help.autodesk.com/cloudhelp/2019/ENU/Maya-Tech-Docs/CommandsPython/blendShape.html

"""

import time
import numpy
from scipy import spatial
import json

from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds
from maya import mel

from brenmeta.core import mhCore

from brenmy.geometry import bmSymMesh
from brenmy.utils import bmNodeUtils
from brenmy.utils import bmMObjectUtils
from brenmy.utils import bmBlendshapeUtils
from brenmy.utils import bmDeformerUtils
from brenmy.utils import bmComponentUtils
from brenmy.utils.mesh import bmMeshUtils

LOG = mhCore.get_basic_logger(__name__)


def get_m_mesh(bs_node, index=0):
    bs_m_object = bmMObjectUtils.parse_m_object(
        bs_node,
        # api_type=OpenMayaAnim.MFnGeometryFilter.type()
    )

    bs_fn = OpenMayaAnim.MFnGeometryFilter(bs_m_object)

    mesh_object = bs_fn.getOutputGeometry()[index]

    return mesh_object


class BmBlendshapeTargetPlugs(object):
    """
    """

    def __init__(self, bs_node, target, in_between=None):

        self.in_between = in_between

        self.bs_m_object = bmMObjectUtils.parse_m_object(
            bs_node,
            # api_type=OpenMayaAnim.MFnGeometryFilter.type()
        )

        self.bs_fn = OpenMayaAnim.MFnGeometryFilter(self.bs_m_object)

        if isinstance(target, str):
            self.target_alias = target
            self.target = bmBlendshapeUtils.get_blendshape_target_index(self.bs_fn.name(), target)
        else:
            self.target_alias = bmBlendshapeUtils.get_blendshape_weight_alias(self.bs_fn.name(), target)
            self.target = target

        self.mesh_object = self.bs_fn.getOutputGeometry()[0]

        geo_index = self.bs_fn.indexForOutputShape(self.mesh_object)

        # get plugs

        self.input_target = self.bs_fn.findPlug('inputTarget', False)

        self.input_target_indexed = self.input_target.elementByLogicalIndex(geo_index)

        self.input_target_group = self.input_target_indexed.child(0)

        self.input_target_group_indexed = self.input_target_group.elementByLogicalIndex(self.target)

        self.input_target_item = self.input_target_group_indexed.child(0)

        # a reference shouldn't be kept to this as it could change
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
        # else:
        #     LOG.info( "WARNING target has no input items")
        #     self.input_target_item_indexed = None
        #     self.input_geom = None
        #     self.points = None
        #     self.components = None
        #     # test
        #     LOG.info( "TEST")
        #     self.input_target_item_indexed = self.input_target_item.elementByLogicalIndex(
        #         6000
        #     )
        #
        #     self.input_geom = self.input_target_item_indexed.child(0)
        #     LOG.info( self.input_geom)

    def get_item_indices(self):
        return self.input_target_item.getExistingArrayAttributeIndices()

    def get_data(self):
        """get point and component data

        this is basically our optimized point delta data
        we only get back points that actually have a delta
        then we can get the corresponding components

        """

        point_data_m_object = self.points.asMObject()
        point_data = OpenMaya.MFnPointArrayData(point_data_m_object)

        # get components
        if self.components.isDefaultValue():
            LOG.info("# WARNING # input_components_target_plug isDefaultValue")
            component_list = None
        else:
            components_data_m_object = self.components.asMObject()
            component_list = OpenMaya.MFnComponentListData(components_data_m_object)

        return point_data, component_list


def get_blendshape_target_data(bs_node, target, in_between=None):
    """TODO test more than one inbetween
    """

    target_plugs = BmBlendshapeTargetPlugs(bs_node, target, in_between=in_between)

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
    point_data, component_list = get_blendshape_target_data(bs_node, target, in_between=in_between)
    point_ids = bmComponentUtils.get_all_component_list_elements(component_list)

    if as_numpy:
        delta = numpy.tile([0.0, 0.0, 0.0], (point_count, 1))

        if not len(point_data):
            return None

        delta[point_ids] = numpy.array(point_data)[:, :-1]

        return delta
    else:

        delta = OpenMaya.MPointArray(point_count, OpenMaya.MPoint())

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

    if bmBlendshapeUtils.is_combo(bs_node, target):
        combo_targets = bmBlendshapeUtils.get_combo_targets(bs_node, target)

        for combo_target in combo_targets:
            combo_delta = get_target_delta(bs_node, combo_target, as_numpy=True)

            if combo_delta is not None:
                delta += combo_delta

    return delta


def set_target_delta(bs_node, target, delta, in_between=None, optimise=False, threshold=0.000000001):
    # get plugs
    target_plugs = BmBlendshapeTargetPlugs(bs_node, target, in_between=in_between)

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
        delta = bmMeshUtils.numpy_points_to_m_point_array(delta)

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


def copy_blendshape_target_data(bs_node, src_target, dst_target, in_between=None, dst_in_between=True):
    if isinstance(src_target, str):
        src_target = bmBlendshapeUtils.get_blendshape_target_index(bs_node, src_target)

    if isinstance(dst_target, str):
        dst_target = bmBlendshapeUtils.get_blendshape_target_index(bs_node, dst_target)

    src_point_data, src_component_list = get_blendshape_target_data(
        bs_node, src_target, in_between=in_between
    )

    # copy point data
    dst_point_data = OpenMaya.MFnPointArrayData()
    dst_point_data.create()
    src_point_data.copyTo(dst_point_data.array())

    # copy component data
    dst_component_list = OpenMaya.MFnComponentListData()
    dst_component_list.create()

    for i in range(src_component_list.length()):
        src_component = src_component_list.get(i)
        src_component = OpenMaya.MFnSingleIndexedComponent(src_component)
        src_elements = src_component.getElements()

        dst_component = OpenMaya.MFnSingleIndexedComponent()

        dst_component.create(
            int(src_component.componentType)
        )

        dst_elements = OpenMaya.MIntArray()
        dst_elements.copy(src_elements)

        dst_component.addElements(dst_elements)

        dst_component_list.add(dst_component.object())

    # set data
    if dst_in_between is True:
        if in_between is not None:
            dst_in_between = in_between
        else:
            dst_in_between = None

    dst_target_plugs = BmBlendshapeTargetPlugs(bs_node, dst_target, in_between=dst_in_between)

    # set point data
    dst_target_plugs.points.setMObject(dst_point_data.object())

    # set components
    dst_target_plugs.components.setMObject(dst_component_list.object())

    return True


def reset_blendshape_target_data(bs_node, target, in_between=None, sl_comp=False):
    """Reset target data with empty objects
    TODO make undoable!

    TODO reset data on selected component only (sl_comp)

from brenmy.deformers import bmBlendshape
reload(bmBlendshape)

bs_node = "bodySubD_BS"
target = "Lf_PinkyPsd_z_neg_90"

bmBlendshape.reset_blendshape_target_data(
    bs_node, target
)

    """
    target_plugs = BmBlendshapeTargetPlugs(bs_node, target, in_between=in_between)

    # set points to new empty list
    point_data = OpenMaya.MFnPointArrayData()
    point_data.create()

    target_plugs.points.setMObject(point_data.object())

    # set components to empty MObject
    target_plugs.components.setMObject(OpenMaya.MObject())

    return True


def mirror_target_to(
        bs_node, src_target, dst_target,
        # in_between=None, dst_in_between=True, # TODO do we need this as an arg?
        match_combo=True, match_in_betweens=False,
        verbose=True
):
    """Mirror src target to dst target

    TODO support dst_bs_node? but only if vertex count matches?

    """
    src_target, src_target_index = bmBlendshapeUtils.parse_target_arg(bs_node, src_target)
    dst_target, dst_target_index = bmBlendshapeUtils.parse_target_arg(bs_node, dst_target)

    if verbose:
        LOG.info(
            "mirroring target {} to {} ({})".format(src_target, dst_target, bs_node)
        )

    # get current symmetry settings
    current_sym_mode = cmds.symmetricModelling(query=True, symmetry=True)
    # TODO other settings

    # get in-betweens
    target_plugs = BmBlendshapeTargetPlugs(bs_node, src_target_index, in_between=None)
    shape_indices = target_plugs.get_item_indices()
    in_between_indices = shape_indices[:-1]
    # TODO check target in-betweens?

    # match combo
    if bmBlendshapeUtils.is_combo(bs_node, src_target) and match_combo:
        base_mesh = cmds.blendShape(bs_node, query=True, geometry=True)[0]

        bmBlendshapeUtils.match_combo(
            bs_node, base_mesh, bs_node, src_target, dst_combo=dst_target
        )

        # combo in-betweens not supported with combos just yet
        # TODO?
        # match_in_betweens = False

    # match in-between
    if match_in_betweens:
        match_target_in_betweens(bs_node, bs_node, src_target, dst_target=dst_target, verbose=verbose)

    # mirror deltas
    cmds.blendShape(
        bs_node,
        edit=True,
        resetTargetDelta=[0, dst_target_index]
    )

    cmds.blendShape(
        bs_node,
        edit=True,
        copyDelta=[0, src_target_index, dst_target_index]
    )

    for i, in_between_index in enumerate(in_between_indices):
        if verbose:
            LOG.info("    copying in-between delta: {}".format(in_between_index))

        copy_blendshape_target_data(
            bs_node, src_target, dst_target, in_between=i, dst_in_between=True
        )

        # note the native method didn't seem to work
        # TODO investigate how it's meant to work
        # cmds.blendShape(
        #     bs_node,
        #     edit=True,
        #     copyInBetweenDelta=[0, 1, src_target_index, dst_target_index],
        # )

    # LOG.info( "    flipping target")

    # TODO topo space
    cmds.blendShape(
        bs_node,
        edit=True,
        flipTarget=[0, dst_target_index],
        symmetrySpace=1,  # object
        symmetryAxis="X",
    )

    # reset symmetry settings
    cmds.symmetricModelling(symmetry=current_sym_mode)

    # LOG.info( "done")

    return True


def mirror_target_to_sl(
        find, replace,
        # in_between=None, dst_in_between=True,
        match_combo=True, match_in_betweens=False, verbose=True
):
    shape_editor_sl = mel.eval("getShapeEditorTreeviewSelection(24)")

    if not shape_editor_sl:
        raise mhCore.MHError("Select a target in the Maya shape editor to mirror")

    for item in shape_editor_sl:
        bs_node, src_target_index = item.split(".")

        src_target_index = int(src_target_index)

        src_target = bmBlendshapeUtils.get_blendshape_weight_alias(bs_node, src_target_index)

        dst_target = src_target.replace(find, replace)

        mirror_target_to(
            bs_node, src_target_index, dst_target,
            match_combo=True, match_in_betweens=True, verbose=verbose
        )

        # if bmBlendshapeUtils.is_combo(bs_node, src_target):
        #     base_mesh = cmds.blendShape(bs_node, query=True, geometry=True)[0]
        #
        #     bmBlendshapeUtils.match_combo(
        #         bs_node, base_mesh, bs_node, src_target, dst_combo=dst_target
        #     )
        #
        #     mirror_target_to(
        #         bs_node, src_target_index, dst_target,
        #         in_between=None, dst_in_between=None, verbose=False
        #     )
        #
        # else:
        #     if match_in_betweens:
        #         match_target_in_betweens(bs_node, bs_node, src_target, dst_target=dst_target, verbose=verbose)
        #
        #     mirror_target_to(
        #         bs_node, src_target_index, dst_target,
        #         in_between=in_between, dst_in_between=dst_in_between, verbose=False
        #     )

    return True


def mirror_target_from_sl_to_sl(
        match_combo=True, match_in_betweens=False, verbose=True
):
    shape_editor_sl = mel.eval("getShapeEditorTreeviewSelection(24)")

    if not shape_editor_sl:
        raise mhCore.MHError("Select a targets in the Maya shape editor to mirror from and to")

    bs_node, src_target_index = shape_editor_sl[0].split(".")
    dst_bs_node, dst_target_index = shape_editor_sl[1].split(".")

    src_target_index = int(src_target_index)
    dst_target_index = int(dst_target_index)

    mirror_target_to(
        bs_node, src_target_index, dst_target_index,
        match_combo=True, match_in_betweens=True, verbose=verbose
    )

    return True


def bake_inbetween_delta_sl():
    """Copy inbetween target data to full target

from brenmy.deformers import bmBlendshape
reload(bmBlendshape)
bmBlendshape.bake_inbetween_delta_sl()

    """
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets()

    if not in_betweens:
        raise mhCore.MHError("please select an inbetween target to bake")

    bs_node, target_index, in_between_index = in_betweens[0]

    LOG.info("baking inbetween delta: {} {} {}".format(bs_node, target_index, in_between_index))

    # reset_blendshape_target_data(
    #     bs_node, target_index, in_between=None
    # )

    copy_blendshape_target_data(
        bs_node, target_index, target_index, in_between=in_between_index, dst_in_between=None
    )

    return True


def reset_target_sl(in_between=None):
    """
    Note with the native maya command if in-between is None
    then the target and all in-betweens will be reset.

    If we only want to reset the target and leave the in-betweens
    as is then use reset_blendshape_target_data.

    """
    shape_editor_sl = mel.eval("getShapeEditorTreeviewSelection(24)")

    if not shape_editor_sl:
        raise mhCore.MHError("Select a target in the Maya shape editor to mirror")

    for target_attr in shape_editor_sl:
        bs_node, target_index = target_attr.split(".")
        target_index = int(target_index)

        # aliases = bmBlendshapeUtils.get_blendshape_weight_aliases(bs_node, as_dict=True)
        # target_name = aliases[target_index]
        target_name = bmBlendshapeUtils.get_blendshape_weight_alias(bs_node, target_index)

        if in_between is not None:
            if not isinstance(in_between, int):
                raise mhCore.MHError("In-between value must be int")

            if in_between < 5000:
                target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=None)
                shape_indices = target_plugs.get_item_indices()
                in_between = shape_indices[in_between]

            LOG.info(
                "Resetting target in-between delta {} {} ({})".format(target_name, in_between, bs_node)
            )

            cmds.blendShape(
                bs_node,
                edit=True,
                resetTargetDelta=[0, target_index],
                inBetweenIndex=in_between
            )

        else:
            LOG.info(
                "Resetting target delta {} ({})".format(target_name, bs_node)
            )

            cmds.blendShape(
                bs_node,
                edit=True,
                resetTargetDelta=[0, target_index],
            )

    return True


def reset_target_sl_component(prune_component=False, in_between=None):
    """Reset delta's for selected components only
    # TODO get in-between selection?

    TODO we can assume the component list from the plug is for a single mesh
        get vertex ids for all component elements
        get which selected vert ids are in the target component ids
        get the array indices for the contained ids
        remove indexed items from points list and component id list
        make a new point array and new component array from pruned lists

    """

    # get component selection
    # TODO multiple selections
    active_sel = OpenMaya.MGlobal.getActiveSelectionList()
    mesh_obj, comp_obj = active_sel.getComponent(0)
    vertex_comp_fn = OpenMaya.MFnSingleIndexedComponent(comp_obj)
    sl_vert_ids = list(vertex_comp_fn.getElements())
    mesh_fn = OpenMaya.MFnMesh(mesh_obj)
    mesh_name = mesh_fn.name()

    # get target selection
    shape_editor_sl = mel.eval("getShapeEditorTreeviewSelection(24)")

    if not shape_editor_sl:
        raise mhCore.MHError("Select a target in the Maya shape editor to mirror")

    # loop through targets
    for target_attr in shape_editor_sl:
        bs_node, target_index = target_attr.split(".")
        target_index = int(target_index)

        # aliases = bmBlendshapeUtils.get_blendshape_weight_aliases(bs_node, as_dict=True)
        # target_name = aliases[target_index]

        # check bs node deforms given mesh
        deformed_meshes = cmds.blendShape(
            bs_node, query=True, geometry=True
        )

        deformed_meshes += [cmds.listRelatives(i, parent=True)[0] for i in deformed_meshes]

        if mesh_name not in deformed_meshes:
            raise mhCore.MHError(
                "Selected blendShape does not deform the given mesh: {} {}".format(bs_node, mesh_name)
            )

        # get target points and component
        target_point_data, target_component_list = get_blendshape_target_data(
            bs_node, target_index, in_between=in_between
        )

        target_points = list(target_point_data.array())

        target_vert_ids = bmComponentUtils.get_all_component_list_elements(target_component_list)
        target_vert_ids = list(target_vert_ids)

        # TODO optimize using numpy
        #   we'd probably need to repeat and reshape arrays to be comparable
        omit_ids = [i for i in target_vert_ids if i in sl_vert_ids]
        omit_list_ids = [target_vert_ids.index(i) for i in omit_ids]

        if prune_component:
            # remove selected vert ids
            pruned_points = numpy.delete(target_points, omit_list_ids, axis=0).tolist()
            pruned_vert_ids = numpy.delete(target_vert_ids, omit_list_ids, axis=0).tolist()

            # construct pruned component data
            pruned_component_list = OpenMaya.MFnComponentListData()
            pruned_component_list.create()

            pruned_component = OpenMaya.MFnSingleIndexedComponent()

            pruned_component.create(
                int(vertex_comp_fn.componentType)
            )

            pruned_elements = OpenMaya.MIntArray(pruned_vert_ids)

            pruned_component.addElements(pruned_elements)

            pruned_component_list.add(pruned_component.object())

            # construct pruned point data
            pruned_point_array = OpenMaya.MPointArray(pruned_points)

            pruned_point_data = OpenMaya.MFnPointArrayData()
            pruned_point_data.create(pruned_point_array)

            # set target pruned points and component
            target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=in_between)

            target_plugs.points.setMObject(pruned_point_data.object())

            target_plugs.components.setMObject(pruned_component_list.object())

        else:
            reset_points = [
                OpenMaya.MPoint() if i in omit_list_ids else target_point
                for i, target_point in enumerate(target_points)
            ]

            # construct pruned point data
            reset_point_array = OpenMaya.MPointArray(reset_points)

            reset_point_data = OpenMaya.MFnPointArrayData()
            reset_point_data.create(reset_point_array)

            # set target pruned points and component
            target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=in_between)

            target_plugs.points.setMObject(reset_point_data.object())

    return True


def get_inbetween_indices(bs_node, target):
    target_name, target_index = bmBlendshapeUtils.parse_target_arg(bs_node, target)
    target_plugs = BmBlendshapeTargetPlugs(bs_node, target, in_between=None)
    inbetween_indices = list(target_plugs.get_item_indices())[:-1]
    return inbetween_indices


def get_inbetween_values(bs_node, target):
    indices = get_inbetween_indices(bs_node, target)
    values = [(i - 5000) / 1000.0 for i in indices]
    return values, indices


def connect_targets(bs_node, targets):
    existing_targets = bmBlendshapeUtils.get_blendshape_weight_aliases(bs_node)

    for target in targets:
        target_name = target.split("|")[-1]

        # TODO turn this into a convention
        if target_name[-7:-4] == "_IB":
            in_between_index = int(target_name[-4:])
            target_name = target_name[:-7]
        else:
            in_between_index = None

        if target_name not in existing_targets:
            # LOG.info( "no target found, skipping: {}".format(target_name))
            continue

        target_plugs = BmBlendshapeTargetPlugs(bs_node, target_name, in_between=in_between_index)

        if target_plugs.input_geom is None:
            raise mhCore.MHError(
                "Target has no input geom plug: {} {}".format(bs_node, target_name)
            )

        LOG.info(
            "connecting: {}  -> {}".format(target, target_plugs.input_geom.name())
        )

        cmds.connectAttr(
            "{}.worldMesh[0]".format(target),
            target_plugs.input_geom.name()
        )

    return True


def match_target_in_betweens(src_bs_node, dst_bs_node, target, dst_target=None, verbose=False):
    """stuff
    """
    target, target_index = bmBlendshapeUtils.parse_target_arg(src_bs_node, target)

    if dst_target is None:
        dst_target = target

    dst_target_index = bmBlendshapeUtils.get_blendshape_target_index(dst_bs_node, dst_target)

    target_plugs = BmBlendshapeTargetPlugs(src_bs_node, target_index, in_between=None)
    item_indices = target_plugs.get_item_indices()
    in_between_indices = item_indices[:-1]

    dst_target_plugs = BmBlendshapeTargetPlugs(dst_bs_node, dst_target_index, in_between=None)
    dst_item_indices = dst_target_plugs.get_item_indices()

    for in_between_index in in_between_indices:
        if in_between_index in dst_item_indices:
            continue

        if verbose:
            LOG.info(
                "matching inbetween target: {}.{} -> {}.{} [{}]".format(
                    src_bs_node, target, dst_bs_node, dst_target, in_between_index
                ))

        # create new in-between array index
        reset_blendshape_target_data(
            dst_bs_node, dst_target_index, in_between=in_between_index
        )

        in_between_name = cmds.getAttr(
            "{}.inbetweenInfoGroup[{}].inbetweenInfo[{}].inbetweenTargetName".format(
                src_bs_node,
                target_index,
                in_between_index
            ),
        )

        cmds.setAttr(
            "{}.inbetweenInfoGroup[{}].inbetweenInfo[{}].inbetweenTargetName".format(
                dst_bs_node,
                dst_target_index,
                in_between_index
            ),
            in_between_name,
            type="string",
        )

    return True


def match_blendshape_targets(src_bs_node, dst_mesh, dst_bs_node=None, suffix="_blendShape", **bs_kwargs):
    """Create a new blendshape node with empty targets matching src bs node
    Includes in-betweens and combos
    """
    aliases = bmBlendshapeUtils.get_blendshape_weight_aliases(src_bs_node)

    if dst_bs_node is None:
        dst_bs_node = "{}{}".format(dst_mesh, suffix)

    if not cmds.objExists(dst_bs_node):
        dst_bs_node = cmds.blendShape(dst_mesh, name=dst_bs_node, **bs_kwargs)[0]
        dst_aliases = []
    else:
        dst_aliases = bmBlendshapeUtils.get_blendshape_weight_aliases(dst_bs_node)

    for alias in aliases:
        if alias not in dst_aliases:
            # create target
            bmBlendshapeUtils.create_empty_target(
                dst_mesh, dst_bs_node, alias
            )

        # match in betweens
        match_target_in_betweens(
            src_bs_node, dst_bs_node, alias
        )

    # match combos
    for alias in aliases:
        combo_input = cmds.listConnections(
            "{}.{}".format(src_bs_node, alias),
            source=True,
            destination=False,
            type="combinationShape"
        )

        if not combo_input:
            continue

        bmBlendshapeUtils.match_combo(
            src_bs_node, dst_mesh, dst_bs_node, alias
        )

    return dst_bs_node


def create_corrective_sl(mesh=None, corrective=None):
    # TODO in betweens
    # TODO blend in base mesh?

    # get selected meshes if not given
    sl_meshes = bmMeshUtils.get_selected_mesh_names(transform=True)

    if mesh is None and corrective is None and not sl_meshes:
        if not sl_meshes:
            raise mhCore.MHError("Please select mesh and corrective")

    if mesh is None:
        mesh = sl_meshes[0]

        if corrective is None:
            corrective = sl_meshes[1]

    if corrective is None:
        corrective = sl_meshes[0]

    # get selected target from the shape editor
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets()

    if in_betweens:
        bs_node, target_index, in_between_index = in_betweens[0]
    else:
        bs_node, target_index = targets[0]
        in_between_index = None

    target_name = cmds.aliasAttr("{}.weight[{}]".format(bs_node, target_index), query=True)

    # check bs node deforms given mesh
    deformed_meshes = cmds.blendShape(
        bs_node, query=True, geometry=True
    )

    deformed_meshes += [cmds.listRelatives(i, parent=True)[0] for i in deformed_meshes]

    if mesh not in deformed_meshes:
        raise mhCore.MHError(
            "Selected blendShape does not deform the given mesh: {} {}".format(bs_node, mesh)
        )

    # invert shape
    delta_mesh = cmds.invertShape(mesh, corrective)

    delta_mesh_name = "{}_{}".format(corrective, target_name)

    if in_between_index:
        delta_mesh_name = "{}_IB{}".format(delta_mesh_name, in_between_index)

    delta_mesh = cmds.rename(delta_mesh, delta_mesh_name)

    cmds.sets(delta_mesh, edit=True, forceElement="initialShadingGroup")

    # replace target
    target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=in_between_index)

    # TODO what happens if there's already a connected mesh?
    cmds.connectAttr(
        "{}.worldMesh[0]".format(delta_mesh),
        target_plugs.input_geom.name(),
        force=True
    )

    return True


def remove_target(bs_node, target, in_between=None):
    """TODO in-between
    TODO unittest code:

from brenmy.utils import bmBlendshapeUtils
reload(bmBlendshapeUtils)

bs_node = "pantsSubD_BS"
target_name = "Lf_Ankle_x_neg_50"

print bmBlendshapeUtils.get_blendshape_target_index(bs_node, target_name)

from brenmy.deformers import bmBlendshape

bmBlendshape.remove_target(bs_node, target_name)

target_name = "Lf_Ankle_x_pos_50"
print bmBlendshapeUtils.get_blendshape_target_index(bs_node, target_name)

    """
    target, target_index = bmBlendshapeUtils.parse_target_arg(bs_node, target)

    target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=in_between)

    cmds.removeMultiInstance(
        target_plugs.input_target_group_indexed.name(),
        b=True  # break any existing connections
    )

    alias = cmds.aliasAttr("{}.w[{}]".format(bs_node, target_index), query=True)

    if alias:
        cmds.aliasAttr("{}.{}".format(bs_node, alias), remove=True)

    cmds.removeMultiInstance(
        "{}.w[{}]".format(bs_node, target_index),
        b=True  # break any existing connections
    )

    return True


def create_target(bs_node, points, name, target_index):
    # TODO in between support
    # TODO check points against geometry
    # TODO check points is flat list of MPoints

    bs_node = bmNodeUtils.validate_node_arg(
        "bs_node", bs_node, node_type="blendShape"
    )
    # get plug for new target index
    target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index)  # , in_between=in_between)

    # get mesh
    mesh_fn = OpenMaya.MFnMesh(target_plugs.mesh_object)
    base_points = mesh_fn.getPoints()

    # get delta
    point_deltas = [
        point - base_point for point, base_point in zip(points, base_points)
    ]

    # set points to new point array data
    point_array = OpenMaya.MPointArray(point_deltas)

    point_data = OpenMaya.MFnPointArrayData()
    point_data.create()
    point_data.set(point_array)

    target_plugs.points.setMObject(point_data.object())

    # set components to all points
    point_count = len(points)
    elements = OpenMaya.MIntArray([i for i in range(point_count)])

    component_fn = OpenMaya.MFnSingleIndexedComponent()
    component_fn.create(OpenMaya.MFn.kMeshVertComponent)
    component_fn.addElements(elements)

    component_list = OpenMaya.MFnComponentListData()
    component_list.create()

    component_list.add(component_fn.object())

    target_plugs.components.setMObject(component_list.object())

    # set name
    w_attr = "{}.w[{}]".format(bs_node, target_index)

    cmds.getAttr(w_attr)

    cmds.aliasAttr(name, w_attr)

    return True


def append_target(bs_node, points, name):
    # TODO in between support

    bs_node = bmNodeUtils.validate_node_arg(
        "bs_node", bs_node, node_type="blendShape"
    )

    target_index = cmds.blendShape(
        bs_node, query=True, weightCount=True
    )

    create_target(bs_node, points, name, target_index)

    return


def bake_weights_to_delta(bs_node, target, weights, in_between=None, optimise=False):
    """

    TODO check weights and delta match

    :param bs_node:
    :param target:
    :param weights:
    :return:
    """
    delta = get_target_delta(
        bs_node, target, in_between=in_between, as_numpy=True,
    )

    if delta is None:
        # TODO warning?
        return True

    weights = numpy.reshape(numpy.repeat(weights, 3), [len(weights), 3])

    weighted_delta = delta * weights

    set_target_delta(
        bs_node, target, weighted_delta, in_between=in_between, optimise=optimise
    )

    return True


def bake_target_weights_to_delta(
        bs_node, target, in_between=None, optimise=False, base_weights=False, reset_weights=True
):
    """

    :param bs_node:
    :param target:
    :param in_between:
    :param optimise:
    :return:
    """
    if base_weights:
        weights = get_blendshape_base_weights(bs_node)
    else:
        weights = get_blendshape_target_weights(bs_node, target)

    bake_weights_to_delta(
        bs_node, target, weights, in_between=in_between, optimise=optimise
    )

    if reset_weights:
        one_weights = numpy.ones(len(weights)).tolist()

        if base_weights:
            set_blendshape_base_weights(bs_node, one_weights)
        else:
            set_blendshape_target_weights(bs_node, target, one_weights)

    return True


def bake_target_weights_to_delta_sl(verbose=True):
    """TODO in betweens
    """

    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets()

    if not targets:
        raise mhCore.MHError("Select a target in the Maya shape editor to bake weights to delta")

    for bs_node, target_index in targets:
        target_index = int(target_index)

        if verbose:
            target_name, _ = bmBlendshapeUtils.parse_target_arg(bs_node, target_index)
            LOG.info("baking target weights: {}.{}".format(bs_node, target_name))

        bake_target_weights_to_delta(
            bs_node, target_index, in_between=None, optimise=False, base_weights=False, reset_weights=True
        )

    return True


def scale_delta_sl_comp(value):
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets()

    vertex_ids = bmMeshUtils.get_selected_vertex_indices()
    vertex_ids = numpy.array(vertex_ids)

    for bs_node, target_index in targets:
        point_data, component_list = get_blendshape_target_data(bs_node, target_index)

        point_data = numpy.array(point_data.array())

        target_vert_ids = bmComponentUtils.get_all_component_list_elements(component_list)
        target_vert_ids = numpy.array(target_vert_ids)

        mask = numpy.in1d(target_vert_ids, vertex_ids)

        point_data[mask] *= value

        point_data = bmMeshUtils.numpy_points_to_m_point_array(point_data)

        dst_point_data = OpenMaya.MFnPointArrayData()
        dst_point_data.create(point_data)

        target_plugs = BmBlendshapeTargetPlugs(bs_node, target_index, in_between=None)

        target_plugs.points.setMObject(dst_point_data.object())

    return True


def create_proxy_combo(bs_node, targets, name=None, create_sculpt_target=True):
    """Create a mesh that combines the given targets.
    Optionally with a sculpt target blendshape.
    """
    # get target indices
    target_indices = []
    target_names = []

    for target in targets:
        if isinstance(target, str):
            target_index = bmBlendshapeUtils.get_blendshape_target_index(bs_node, target)
            target_name = target
        else:
            target_index = target
            target_name = bmBlendshapeUtils.get_blendshape_weight_alias(bs_node, target)

        target_indices.append(target_index)
        target_names.append(target_name)

    if name:
        proxy_combo = name
    else:
        proxy_combo = "_".join(target_names)
        proxy_combo = "{}_proxyCombo".format(proxy_combo)

    target_transform, target_shape = bmDeformerUtils.duplicate_orig_mesh(bs_node, proxy_combo, parent=None)

    target_mesh_fn = OpenMaya.MFnMesh(target_shape)
    point_count = target_mesh_fn.numVertices

    # sum targets and apply to unsplit target
    summed_delta = numpy.array([[0.0, 0.0, 0.0] for _ in range(point_count)])

    for target_index in target_indices:
        if bmBlendshapeUtils.is_combo(bs_node, target_index):
            delta = get_summed_combo_delta(bs_node, target_index)
        else:
            delta = get_target_delta(bs_node, target_index, as_numpy=True)

        if delta is not None:
            summed_delta += delta

    # set points directly
    # points = bmMeshUtils.get_points(proxy_combo, as_numpy=True)
    # bmMeshUtils.set_points(proxy_combo, points + summed_delta)

    if create_sculpt_target:
        # create sculpt target and apply summed delta as a target
        target_bs_node = cmds.deformer(
            proxy_combo, type="blendShape", name="{}_blendShape".format(proxy_combo)
        )[0]

        bmBlendshapeUtils.create_empty_target(
            proxy_combo, target_bs_node, "sculpt", default=1.0
        )

        bmBlendshapeUtils.create_empty_target(
            proxy_combo, target_bs_node, "comboDelta", default=1.0
        )

        set_target_delta(target_bs_node, "comboDelta", summed_delta)

    else:
        # set points directly
        points = bmMeshUtils.get_points(proxy_combo, as_numpy=True)
        bmMeshUtils.set_points(proxy_combo, points + summed_delta)

    # add metadata
    cmds.addAttr(
        proxy_combo,
        longName="source_shapes",
        dataType="string"
    )

    meta_data = {
        "blendShape": bs_node,
        "targets": targets,
        "target_indices": target_indices,
    }

    meta_data = json.dumps(meta_data)

    cmds.setAttr(
        "{}.source_shapes".format(proxy_combo),
        meta_data,
        type="string"
    )

    return proxy_combo


def create_proxy_combo_sl():
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets(force_single_bs_node=True)

    bs_node = targets[0][0]

    target_indices = []

    for target_bs_node, target_index in targets:
        target_indices.append(target_index)

    return create_proxy_combo(bs_node, target_indices)


def apply_proxy_combo(proxy_combo, rebuild=True):
    """Distributes the combo sculpt deltas across the original targets.

    Deltas are automatically weighted per target
    according to their contribution to the proxy combo.

    """
    point_count = cmds.polyEvaluate(proxy_combo, vertex=True)

    meta_data = cmds.getAttr("{}.source_shapes".format(proxy_combo))
    meta_data = json.loads(meta_data)

    bs_node = meta_data["blendShape"]
    target_indices = meta_data["target_indices"]

    # get sculpt delta
    sculpt_bs_node = "{}_blendShape".format(proxy_combo)

    sculpt_delta = get_target_delta(sculpt_bs_node, 0, as_numpy=True)

    if sculpt_delta is None:
        return None

    # get existing deltas
    deltas = []
    delta_lengths = []

    summed_delta = numpy.array([[0.0, 0.0, 0.0] for _ in range(point_count)])
    summed_delta_length = numpy.zeros(point_count)

    for target_index in target_indices:
        if bmBlendshapeUtils.is_combo(bs_node, target_index):
            delta = get_summed_combo_delta(bs_node, target_index)
        else:
            delta = get_target_delta(bs_node, target_index, as_numpy=True)

        deltas.append(delta)
        delta_length = numpy.linalg.norm(delta, axis=1)
        delta_lengths.append(delta_length)
        summed_delta_length += delta_length

    # calculate weights and split sculpt deltas
    for target_index, delta, delta_length in zip(
            target_indices, deltas, delta_lengths
    ):
        weights = numpy.divide(
            delta_length,
            summed_delta_length,
            out=numpy.zeros_like(delta_length, dtype=float),
            where=summed_delta_length != 0
        )

        weights = numpy.reshape(numpy.repeat(weights, 3), [point_count, 3])

        split_delta = sculpt_delta * weights

        if rebuild:
            # TODO check if it's already been rebuilt
            #   then edit the existing sculpt target (if that exists)

            # rebuild target and apply split sculpt as a blendshape
            rebuild_result = cmds.sculptTarget(bs_node, edit=True, regenerate=True, target=target_index)

            if rebuild_result:
                target_mesh = rebuild_result[0]

                target_bs_node = cmds.deformer(
                    target_mesh, type="blendShape", name="{}_blendShape".format(target_mesh)
                )[0]

                bmBlendshapeUtils.create_empty_target(
                    target_mesh, target_bs_node, "sculpt"
                )
            else:
                # target already rebuilt
                target_mesh = bmBlendshapeUtils.get_blendshape_weight_alias(bs_node, target_index)
                target_bs_node = "{}_blendShape".format(target_mesh)

            set_target_delta(target_bs_node, 0, split_delta)

        else:
            # apply split delta directly
            delta += split_delta
            set_target_delta(bs_node, target_index, delta)

    return True

def apply_proxy_combo_sl(rebuild=True):
    sl = cmds.ls(sl=True, type="transform")

    if not sl:
        raise mhCore.MHError("Please select a proxy combo to apply")

    # TODO other checks

    proxy_combo = sl[0]

    apply_proxy_combo(proxy_combo, rebuild=rebuild)

    return True


def create_live_unsplit_target(bs_node, targets, name=None):
    """Create a mesh that unsplits the given targets and connects the split targets via weights
    """

    if not name:
        name = "_".join(targets)
        name = "{}_unsplit".format(name)

    target_transform, target_shape = bmDeformerUtils.duplicate_orig_mesh(bs_node, name, parent=None)

    target_mesh_fn = OpenMaya.MFnMesh(target_shape)
    point_count = target_mesh_fn.numVertices

    # get target indices
    target_indices = []

    for target in targets:
        if isinstance(target, str):
            target_index = bmBlendshapeUtils.get_blendshape_target_index(bs_node, target)
        else:
            target_index = target

        target_indices.append(target_index)

    # ensure targets are rebuilt
    # TODO check they are not already rebuilt and get them if they are
    target_meshes = []
    split_targets = []

    for target_index in target_indices:
        target_mesh = cmds.sculptTarget(bs_node, edit=True, regenerate=True, target=target_index)[0]
        target_meshes.append(target_mesh)

        split_target = cmds.duplicate(name, name="{}_split".format(target_mesh))[0]
        split_targets.append(split_target)

    # sum targets and apply to unsplit target
    deltas = []
    delta_lengths = []

    summed_delta = numpy.array([[0.0, 0.0, 0.0] for _ in range(point_count)])
    summed_delta_length = numpy.zeros(point_count)

    for target_index in target_indices:
        delta = get_target_delta(bs_node, target_index, as_numpy=True)
        delta_length = numpy.linalg.norm(delta, axis=1)
        summed_delta += delta
        summed_delta_length += delta_length
        deltas.append(delta)
        delta_lengths.append(delta_length)

    points = bmMeshUtils.get_points(name, as_numpy=True)
    bmMeshUtils.set_points(name, points + summed_delta)

    # blendshape unsplit target to targets and apply weights
    for target_mesh, split_target, delta, delta_length in zip(
            target_meshes, split_targets, deltas, delta_lengths
    ):

        weights = numpy.divide(
            delta_length,
            summed_delta_length,
            out=numpy.zeros_like(delta_length, dtype=float),
            where=summed_delta_length != 0
        )

        split_bs_node = cmds.blendShape(
            name,
            split_target,
            name="{}_blendShape".format(split_target)
        )[0]

        cmds.setAttr(
            "{}.w[0]".format(split_bs_node), 1.0
        )

        set_blendshape_target_weights(split_bs_node, 0, weights)

        target_bs_node = cmds.blendShape(
            split_target,
            target_mesh,
            name="{}_blendShape".format(target_mesh)
        )[0]

        cmds.setAttr(
            "{}.w[0]".format(target_bs_node), 1.0
        )

    return True


def add_deltas_sl():
    """Add deltas of selected targets and apply to last selected target
    """
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets(force_single_bs_node=True)

    bs_node = targets[0][0]

    target_indices = [i[1] for i in targets]

    deltas = get_summed_deltas(bs_node, target_indices)

    set_target_delta(bs_node, target_indices[-1], deltas)

    return True


def subtract_deltas_sl():
    """Sum deltas of selected targets except for the last selected target and subtract from last target
    """
    targets, in_betweens = bmBlendshapeUtils.get_selected_shape_editor_targets(force_single_bs_node=True)

    bs_node = targets[0][0]

    target_indices = [i[1] for i in targets]

    summed_deltas = get_summed_deltas(bs_node, target_indices[:-1])

    deltas = get_target_delta(bs_node, target_indices[-1], as_numpy=True)
    deltas -= summed_deltas

    set_target_delta(bs_node, target_indices[-1], deltas)

    return True
