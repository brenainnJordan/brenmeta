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


def get_m_mesh(bs_node, index=0):
    bs_m_object = mhMayaUtils.parse_m_object(
        bs_node,
        # api_type=OpenMayaAnim.MFnGeometryFilter.type()
    )

    bs_fn = OpenMayaAnim.MFnGeometryFilter(bs_m_object)

    mesh_object = bs_fn.getOutputGeometry()[index]

    return mesh_object


def get_blendshape_weight_aliases(bs_node, as_dict=False):

    bmNodeUtils.validate_node_arg(
        "bs_node", bs_node, node_type="blendShape", exists=True,
        err_suffix="Cannot get blendshape weight aliases"
    )

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

    raise bmCore.BmError("No target found: {}".format(target_name))


def parse_target_arg(bs_node, target):
    if isinstance(target, bpCore.BASESTRING):
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


class BmBlendshapeTargetPlugs(object):
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
    point_ids = mhMayaUtils.get_all_component_list_elements(component_list)

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

    if is_combo(bs_node, target):
        combo_targets = get_combo_targets(bs_node, target)

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
