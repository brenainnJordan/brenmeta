"""
TODO utils to transfer eye meshes etc
"""

from maya import cmds
from maya.api import OpenMaya

from . import mhMayaUtils
from . import mhCore

L_EYE_MID_VERTS = "[161:192]"
R_EYE_MID_VERTS = "[161:192]"

L_EYELID_EDGES = [
    29882, 29884, 29902, 29910, 29943,
    29947, 29988, 29990, 30056, 30058,
    30081, 30083, 30098, 30100, 30276,
    30278, 30307, 30309, 30327, 30329,
    30373, 30375, 30388, 30396, 30402,
    30404, 30422, 30424, 30447, 30452,
    30548, 30552, 30582, 30588, 30750,
    30756, 30760, 30768, 30805, 30807,
    30842, 30850, 30857, 30859, 30927,
    30930, 34103, 34106, 34137, 34140,
    34373, 34378, 34419, 34422, 34437,
    34440, 34460, 34462, 35857, 35860,
]

R_EYELID_EDGES = [
    5794, 5796, 5808, 5812, 5855,
    5861, 5894, 5896, 5968, 5970,
    5988, 5990, 6008, 6010, 6181,
    6183, 6218, 6220, 6236, 6238,
    6282, 6284, 6294, 6298, 6312,
    6314, 6327, 6329, 6354, 6357,
    6454, 6458, 6488, 6492, 6656,
    6660, 6666, 6670, 6712, 6714,
    6748, 6752, 6765, 6767, 6834,
    6837, 10014, 10017, 10044, 10047,
    10280, 10283, 10330, 10333, 10348,
    10351, 10367, 10369, 11770, 11773,
]

L_EDGE_INNER_VERTS = [
    53, 54, 55, 108, 109, 110, 111, 112, 113, 114, 115, 116, 118, 119, 120, 121, 231, 234, 237, 240, 243, 246, 249, 252,
    255, 258, 261, 264
]

L_EDGE_BLEND_VERTS = [
    0, 1, 2, 3, 4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 117, 232, 235, 238, 241, 244, 247, 250, 253, 256, 259, 262, 265
]

R_EDGE_INNER_VERTS = [
    104, 105, 106, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 133, 134, 135, 187, 190, 193, 196, 199, 202, 205,
    208, 211, 214, 217, 220
]

R_EDGE_BLEND_VERTS = [
    57, 58, 59, 60, 61, 62, 63, 64, 72, 73, 74, 75, 76, 77, 132, 186, 189, 192, 195, 198, 201, 204, 207, 210, 213, 216,
    219
]

EDGE_BORDER_VERTS = [
    14, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 52, 67, 68, 69, 70, 71, 78,
    79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 103, 141, 147, 153, 154, 165, 171, 172, 178, 179, 180,
    181, 182, 183, 184, 185, 188, 191, 194, 197, 200, 203, 206, 209, 212, 215, 218, 221, 222, 223, 224, 225, 226, 227,
    228, 229, 230, 233, 236, 239, 242, 245, 248, 251, 254, 257, 260, 263, 266, 267
]

EYE_SHELL_BORDER_VERTS = [
    0, 1, 4, 5, 10, 11, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 31, 32, 39, 40, 41, 44, 45, 46, 47, 48, 49, 54, 55, 56,
    119, 120, 122, 123, 125, 127, 130, 132, 134, 136, 138, 140, 142, 144, 146, 147, 150, 151, 154, 156, 157, 160, 161,
    163, 165, 168, 169, 171, 173, 175, 276, 277, 280, 281, 286, 287, 288, 289, 290, 291, 292, 295, 296, 297, 298, 299,
    307, 308, 315, 316, 317, 320, 321, 322, 323, 324, 325, 330, 331, 332, 395, 396, 398, 399, 401, 403, 406, 408, 410,
    412, 414, 416, 418, 420, 422, 423, 426, 427, 430, 432, 433, 436, 437, 439, 441, 444, 445, 447, 449, 451
]

EYE_SHELL_BLEND_VERTS = [
    312, 333, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519,
    520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542,
    543, 544, 545, 546
]

L_EYE_SHELL_PROJECTION_VERTS = [
    278, 279, 282, 283, 284, 285, 293, 294, 300, 301, 302, 303, 304, 305, 306, 310, 318, 319, 326, 327, 335, 339, 340,
    341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370,
    371, 372, 373, 374, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 397, 400,
    402, 404, 405, 407, 409, 411, 413, 425, 429, 440, 442, 443, 446, 448, 450, 452, 453, 454, 455, 456, 457, 458, 459,
    460, 461, 462, 463, 468, 469, 470, 471, 472, 473, 474, 475, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490,
    491, 492, 493, 494, 495, 496, 497, 498, 548, 549, 550, 551
]

R_EYE_SHELL_PROJECTION_VERTS = [
    2, 3, 6, 7, 8, 9, 17, 18, 24, 25, 26, 27, 28, 29, 30, 34, 42, 43, 50, 51, 59, 63, 64, 65, 66, 67, 68, 69, 70, 71,
    72, 73, 74, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 102, 103, 104, 105, 106, 107, 108,
    109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 121, 124, 126, 128, 129, 131, 133, 135, 137, 149, 153, 164, 166,
    167, 170, 172, 174, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 192, 193, 194, 195, 196, 197, 198,
    199, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 272, 273, 274,
    275
]

L_EYE_SHELL_CORNER_VERTS = [
    309, 310, 311, 312, 313, 314, 327, 328, 329, 333, 334, 336, 337, 338, 339, 351, 352, 353, 354, 355, 356, 357, 358,
    375, 376, 377, 378, 415, 417, 419, 421, 424, 428, 431, 434, 435, 438, 464, 465, 466, 467, 476, 477, 478, 479, 517,
    518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528
]

R_EYE_SHELL_CORNER_VERTS = [
    33, 34, 35, 36, 37, 38, 51, 52, 53, 57, 58, 60, 61, 62, 63, 75, 76, 77, 78, 79, 80, 81, 82, 99, 100, 101, 102, 139,
    141, 143, 145, 148, 152, 155, 158, 159, 162, 188, 189, 190, 191, 200, 201, 202, 203, 241, 242, 243, 244, 245, 246,
    247, 248, 249, 250, 251, 252
]


def create_cone_from_edges(name, mesh, edge_ids, origin, scale=1.0):
    """stuff
    """
    mesh_dag = mhMayaUtils.parse_dag_path(mesh)

    edge_vert_ids = mhMayaUtils.edges_to_vertex_ids(mesh_dag, edge_ids)

    # get mesh points
    # get point positions
    src_mesh_fn = OpenMaya.MFnMesh(mesh_dag)
    src_mesh_points = src_mesh_fn.getPoints(OpenMaya.MSpace.kWorld)

    origin = OpenMaya.MVector(origin)

    # re-order points in sequence
    sorted_src_point_ids = [edge_vert_ids[0]]

    src_vert_it = OpenMaya.MItMeshVertex(mesh_dag)
    src_vert_it.setIndex(edge_vert_ids[0])

    connected_vert_ids = src_vert_it.getConnectedVertices()

    # pick either to start
    connected_edge_vert_ids = [i for i in connected_vert_ids if i in edge_vert_ids]
    sorted_src_point_ids.append(connected_edge_vert_ids[0])

    for i in range(len(edge_vert_ids) - 2):
        # TODO check there is exactly two connected points
        src_vert_it.setIndex(sorted_src_point_ids[-1])
        connected_vert_ids = src_vert_it.getConnectedVertices()
        # connected_edge_ids = [i for i in connected_vert_ids if i in edge_vert_ids]

        # get point that is not already in the list
        connected_vert_found = False
        for connected_vert_id in connected_vert_ids:
            if connected_vert_id not in edge_vert_ids:
                continue
            if connected_vert_id not in sorted_src_point_ids:
                sorted_src_point_ids.append(connected_vert_id)
                connected_vert_found = True
                break

        if not connected_vert_found:
            raise Exception("Failed to sort points: {} {} {}".format(
                sorted_src_point_ids[-1], connected_vert_ids, sorted_src_point_ids)
            )

    # print("Sorted edge vertex ids: ({}) {}".format(len(sorted_src_point_ids), sorted_src_point_ids))

    sorted_src_points = [src_mesh_points[i] for i in sorted_src_point_ids]

    # scale
    if scale != 1.0:
        # print(origin)
        # print(sorted_src_points[0])
        deltas = [OpenMaya.MPoint(i - origin) for i in sorted_src_points]
        # print(deltas[0])
        deltas = [i * scale for i in deltas]
        # print(deltas[0])
        sorted_src_points = [i + origin for i in deltas]

    # construct new list of points
    points = [origin] + list(sorted_src_points)
    points = [OpenMaya.MPoint(i) for i in points]

    # list of number of vertices per polygon
    # we want a triangle per src mesh vertex
    polygon_faces = [3] * (len(sorted_src_points) + 1)

    # list of vertex indices that make the
    # the polygons in our mesh
    polygon_connects = []

    for i in range(len(sorted_src_points)):
        # each triangle will connect the first vertex (at the pivot point)
        # to each point and it's adjacent point
        face_verts = [0, i, i + 1]

        polygon_connects += face_verts

    # add last poly to close loop
    polygon_connects += [0, len(sorted_src_points), 1]

    # create the mesh
    mesh_fn = OpenMaya.MFnMesh()
    res = mesh_fn.create(points, polygon_faces, polygon_connects)

    # name the mesh
    mesh_node = OpenMaya.MFnDependencyNode(res)
    mesh_node.setName(name)

    print("Mesh created: {}".format(name))

    return res


def mean(values):
    return sum(values) / len(values)


def get_average_vertex_position(vertices):
    values = cmds.xform(vertices, query=True, translation=True)
    # points = [values[i * 3:(i * 3) + 3] for i in range(int(len(values) / 3))]
    return [mean(values[i::3]) for i in range(3)]


def create_eyelid_wrapper_meshes(head_mesh, l_eye_mesh, r_eye_mesh, prefix=None, scale=1.0):
    # allow pivots to be passed in
    if isinstance(l_eye_mesh, (list, tuple)):
        l_position = l_eye_mesh
    else:
        l_position = get_average_vertex_position("{}.vtx{}".format(l_eye_mesh, L_EYE_MID_VERTS))

    if isinstance(r_eye_mesh, (list, tuple)):
        r_position = r_eye_mesh
    else:
        r_position = get_average_vertex_position("{}.vtx{}".format(r_eye_mesh, R_EYE_MID_VERTS))

    l_mesh = "l_eyelid_wrapper_mesh"
    r_mesh = "r_eyelid_wrapper_mesh"

    if prefix:
        l_mesh = "{}{}".format(prefix, l_mesh)
        r_mesh = "{}{}".format(prefix, r_mesh)

    create_cone_from_edges(l_mesh, head_mesh, L_EYELID_EDGES, l_position, scale=scale)
    create_cone_from_edges(r_mesh, head_mesh, R_EYELID_EDGES, r_position, scale=scale)

    return l_mesh, r_mesh


def snap_eye_edge(eyeball_mesh, edge_mesh, inner_verts, blend_verts, blend_value=0.5):
    """project inner edge loop onto eye and second inner edge loop onto eye with blend

    """
    cmds.DeleteHistory(edge_mesh)

    edge_dag = mhMayaUtils.parse_dag_path(edge_mesh)
    edge_fn = OpenMaya.MFnMesh(edge_dag)

    edge_points = edge_fn.getPoints(space=OpenMaya.MSpace.kWorld)

    inner_points = [edge_points[i] for i in inner_verts]
    blend_points = [edge_points[i] for i in blend_verts]

    eye_dag = mhMayaUtils.parse_dag_path(eyeball_mesh)
    eye_fn = OpenMaya.MFnMesh(eye_dag)

    snapped_inner_points = [
        eye_fn.getClosestPoint(point, OpenMaya.MSpace.kWorld)[0]
        for point in inner_points
    ]

    snapped_blend_points = [
        eye_fn.getClosestPoint(point, OpenMaya.MSpace.kWorld)[0]
        for point in blend_points
    ]

    blended_points = [
        a + ((b - a) * blend_value) for a, b in zip(blend_points, snapped_blend_points)
    ]

    for i, point in zip(inner_verts, snapped_inner_points):
        edge_points[i] = point

    for i, point in zip(blend_verts, blended_points):
        edge_points[i] = point

    edge_fn.setPoints(edge_points)

    return True


def blend_eye_edge(edge_mesh, blend_mesh, blend_value=0.5):
    edge_dag = mhMayaUtils.parse_dag_path(edge_mesh)
    blend_dag = mhMayaUtils.parse_dag_path(blend_mesh)

    edge_fn = OpenMaya.MFnMesh(edge_dag)
    blend_fn = OpenMaya.MFnMesh(blend_dag)

    edge_points = edge_fn.getPoints(space=OpenMaya.MSpace.kWorld)
    blend_points = blend_fn.getPoints(space=OpenMaya.MSpace.kWorld)

    for i in L_EDGE_INNER_VERTS + R_EDGE_INNER_VERTS:
        edge_points[i] = blend_points[i]

    for i in L_EDGE_BLEND_VERTS + R_EDGE_BLEND_VERTS:
        edge_points[i] = edge_points[i] + ((blend_points[i] - edge_points[i]) * blend_value)

    edge_fn.setPoints(edge_points, space=OpenMaya.MSpace.kWorld)

    return True


def project_mesh_onto_eye(mesh, eyeball_mesh, vert_ids, eye_mid_verts, offset):
    """project points from mesh onto eye mesh with offset above eye surface
    """

    mesh_dag = mhMayaUtils.parse_dag_path(mesh)
    mesh_fn = OpenMaya.MFnMesh(mesh_dag)

    points = mesh_fn.getPoints(space=OpenMaya.MSpace.kWorld)

    centroid = get_average_vertex_position("{}.vtx{}".format(eyeball_mesh, eye_mid_verts))
    centroid = OpenMaya.MPoint(centroid)

    eye_dag = mhMayaUtils.parse_dag_path(eyeball_mesh)
    eye_fn = OpenMaya.MFnMesh(eye_dag)

    for i in vert_ids:
        point = points[i]
        vector = OpenMaya.MFloatVector(centroid - point)
        vector = vector.normal()

        intersection = eye_fn.closestIntersection(
            OpenMaya.MFloatPoint(point), vector, OpenMaya.MSpace.kWorld, 10000, True
        )

        hit_point = intersection[0] + (vector * offset * -1.0)

        points[i] = hit_point

    mesh_fn.setPoints(points)

    return True


def blend_points(src_mesh, dst_mesh, vert_ids, blend=1.0):
    src_dag = mhMayaUtils.parse_dag_path(src_mesh)
    src_fn = OpenMaya.MFnMesh(src_dag)

    dst_dag = mhMayaUtils.parse_dag_path(dst_mesh)
    dst_fn = OpenMaya.MFnMesh(dst_dag)

    src_points = src_fn.getPoints(space=OpenMaya.MSpace.kWorld)
    dst_points = dst_fn.getPoints(space=OpenMaya.MSpace.kWorld)

    for i in vert_ids:
        # TODO blend
        dst_points[i] = src_points[i]

    dst_fn.setPoints(dst_points)

    return True




def transfer_eyeball_mesh(
        mesh, src_pivot, dst_pivot, dst_scale, src_prefix="src_",
):
    """stuff
    """

    src_pivot = OpenMaya.MVector(src_pivot)
    dst_pivot = OpenMaya.MVector(dst_pivot)

    # create mesh
    src_mesh = "{}{}".format(src_prefix, mesh)
    cmds.duplicate(src_mesh, name=mesh)
    cmds.parent(mesh, world=True)

    # transform eyeball
    src_points = mhMayaUtils.get_points(src_mesh)
    src_vectors = [i - src_pivot for i in src_points]

    dst_points = [OpenMaya.MPoint((i * dst_scale) + dst_pivot) for i in src_vectors]

    dst_dag = mhMayaUtils.parse_dag_path(mesh)
    dst_fn = OpenMaya.MFnMesh(dst_dag)
    dst_fn.setPoints(dst_points)

    return True



def transfer_eyeball_meshes(
        l_eyeball_mesh, r_eyeball_mesh, l_wrapper_mesh, r_wrapper_mesh, l_orig_wrapper, r_orig_wrapper,
        src_prefix="src_", recalculate_pivots=True,
):
    """stuff
    """

    pivots = []

    for eyeball_mesh, wrapper_mesh, orig_wrapper in [
        (l_eyeball_mesh, l_wrapper_mesh, l_orig_wrapper),
        (r_eyeball_mesh, r_wrapper_mesh, r_orig_wrapper),
    ]:
        # create mesh
        src_eyeball_mesh = "{}{}".format(src_prefix, eyeball_mesh)
        cmds.duplicate(src_eyeball_mesh, name=eyeball_mesh)
        cmds.parent(eyeball_mesh, world=True)

        # get points and pivots from wrapper mesh
        dst_wrapper_points = [OpenMaya.MVector(i) for i in mhMayaUtils.get_points(wrapper_mesh)]
        dst_eye_pivot = dst_wrapper_points.pop(0)

        src_wrapper_points = [OpenMaya.MVector(i) for i in mhMayaUtils.get_points(orig_wrapper)]
        src_eye_pivot = src_wrapper_points.pop(0)

        # approximate eyeball scale difference
        # TODO option to average L/R
        if recalculate_pivots:
            # ignore pivots and use width of wrapper points to estimate scale
            src_x = [i.x for i in src_wrapper_points]
            dst_x = [i.x for i in dst_wrapper_points]
            src_width = max(src_x) - min(src_x)
            dst_width = max(dst_x) - min(dst_x)

            eyeball_scale = dst_width/src_width

        else:
            # use distance between pivot and points to estimate scale

            dst_wrapper_vectors = [i - dst_eye_pivot for i in dst_wrapper_points]
            src_wrapper_vectors = [i - src_eye_pivot for i in src_wrapper_points]

            eyeball_scale = mean([a.length() / b.length() for a, b in zip(dst_wrapper_vectors, src_wrapper_vectors)])

        print("eyeball scale: {} ({})".format(eyeball_scale, eyeball_mesh))

        if recalculate_pivots:
            src_avg_point = mhMayaUtils.get_average_position(src_wrapper_points)
            src_eye_pivot_delta = [a - b for a, b in zip(src_eye_pivot, src_avg_point)]

            dst_avg_point = mhMayaUtils.get_average_position(dst_wrapper_points)

            dst_eye_pivot = OpenMaya.MVector([
                (a * eyeball_scale) + b for a, b in zip(src_eye_pivot_delta, dst_avg_point)
            ])

        # transform eyeball
        src_eyeball_points = mhMayaUtils.get_points(src_eyeball_mesh)
        src_eyeball_vectors = [i - src_eye_pivot for i in src_eyeball_points]

        dst_eyeball_points = [OpenMaya.MPoint((i * eyeball_scale) + dst_eye_pivot) for i in src_eyeball_vectors]

        dst_eyeball_dag = mhMayaUtils.parse_dag_path(eyeball_mesh)
        dst_eyeball_fn = OpenMaya.MFnMesh(dst_eyeball_dag)
        dst_eyeball_fn.setPoints(dst_eyeball_points)

        # store for later
        pivots.append(dst_eye_pivot)

    return pivots


def create_inner_mouth_meshes(
        blend_head,
        src_prefix="src_",
        # head_mesh="head_lod0_mesh",
        teeth_mesh="teeth_lod0_mesh",
        saliva_mesh="saliva_lod0_mesh",
        # cleanup=True,
):
    # src_head_mesh = "{}{}".format(src_prefix, head_mesh)

    src_teeth_mesh = "{}{}".format(src_prefix, teeth_mesh)
    src_saliva_mesh = "{}{}".format(src_prefix, saliva_mesh)

    meshes = [teeth_mesh, saliva_mesh]

    # transfer_grp = cmds.createNode("transform", name="transfer_GRP")

    # blend_head = cmds.duplicate(src_head_mesh, name="head_mouth_blend_mesh")[0]
    # cmds.parent(blend_head, transfer_grp)

    cmds.duplicate(src_teeth_mesh, name=teeth_mesh)
    cmds.duplicate(src_saliva_mesh, name=saliva_mesh)
    cmds.parent(teeth_mesh, saliva_mesh, world=True)

    mhMayaUtils.create_wrap(
        [teeth_mesh],
        blend_head,
        attrs={
            "exclusiveBind": False,
            # weightThreshold=0,
            # maxDistance=0.0,
            # autoWeightThreshold=False,
            # falloffMode=0
        }
    )

    cmds.deltaMush(teeth_mesh, smoothingIterations=50, smoothingStep=1.0)

    mhMayaUtils.create_wrap(
        [saliva_mesh],
        teeth_mesh,
        attrs={
            "exclusiveBind": False,
            # weightThreshold=0,
            # maxDistance=0.0,
            # autoWeightThreshold=False,
            # falloffMode=0
        }
    )

    # bs_node = cmds.blendShape(head_mesh, blend_head)[0]
    # cmds.setAttr("{}.w[0]".format(bs_node), 1.0)
    #
    # # cleanup
    # if cleanup:
    #     meshes = [
    #         i for i in all_meshes
    #         if cmds.objExists(i)
    #     ]
    #
    #     cmds.select(meshes)
    #     cmds.DeleteHistory()
    #
    #     cmds.delete(transfer_grp)

    return meshes


def create_eyewet_meshes(
        cartilage_mesh, edge_mesh, shell_mesh, transfer_grp, blend_head, closed_wrapper_mesh, src_prefix="src_",
):
    """
    stuff
    """
    src_edge_mesh = "{}{}".format(src_prefix, edge_mesh)
    src_shell_mesh = "{}{}".format(src_prefix, shell_mesh)

    meshes = [
        cartilage_mesh, edge_mesh, shell_mesh
    ]

    for mesh in meshes:
        src_mesh = "{}{}".format(src_prefix, mesh)
        cmds.duplicate(src_mesh, name=mesh)
        cmds.parent(mesh, world=True)

    edge_blend_mesh = cmds.duplicate(src_edge_mesh, name="eye_edge_blend_mesh")[0]
    cmds.parent(edge_blend_mesh, transfer_grp)

    shell_blend_mesh = cmds.duplicate(src_shell_mesh, name="eye_shell_blend_mesh")[0]
    cmds.parent(shell_blend_mesh, transfer_grp)

    mhMayaUtils.create_wrap(
        [
            cartilage_mesh, shell_blend_mesh,
            # edge_mesh
            edge_blend_mesh,
        ],
        blend_head,
        attrs={
            "exclusiveBind": True,
            # weightThreshold=0,
            # maxDistance=0.0,
            # autoWeightThreshold=False,
            # falloffMode=0
        }
    )

    mhMayaUtils.create_wrap(
        [
            shell_mesh,
            # edge_mesh,
        ],
        closed_wrapper_mesh,
        attrs={
            "exclusiveBind": False,
            # weightThreshold=0,
            # maxDistance=0.0,
            # autoWeightThreshold=False,
            # falloffMode=0
        }
    )

    mhMayaUtils.create_wrap(
        [
            # edge_blend_mesh,
            edge_mesh
        ],
        shell_mesh,
        attrs={
            "exclusiveBind": False,
            # weightThreshold=0,
            # maxDistance=0.0,
            # autoWeightThreshold=False,
            # falloffMode=0
        }
    )

    return meshes, edge_blend_mesh, shell_blend_mesh

# def snap_eye_shell_border():
#     shell_mesh = "eyeshell_lod0_mesh"
#     shell_blend_mesh = "eye_shell_blend_mesh"
#
#     blend_points(
#         shell_blend_mesh, shell_mesh, EYE_SHELL_BORDER_VERTS + EYE_SHELL_BLEND_VERTS
#     )
#
#     blend_vertices = [
#         "{}.vtx[{}]".format(shell_mesh, i) for i in EYE_SHELL_BLEND_VERTS
#     ]
#
#     cmds.polyAverageVertex(blend_vertices, i=10, ch=False)
#
#     return True

def eyewet_post(edge_mesh, edge_blend_mesh, shell_mesh, shell_blend_mesh, l_eyeball_mesh, r_eyeball_mesh):
    # clean up shell
    cmds.select(shell_mesh)
    cmds.DeleteHistory()

    for eyeball_mesh, verts, eye_mid_verts in [
        (l_eyeball_mesh, L_EYE_SHELL_PROJECTION_VERTS, L_EYE_MID_VERTS),
        (r_eyeball_mesh, R_EYE_SHELL_PROJECTION_VERTS, R_EYE_MID_VERTS),
    ]:
        project_mesh_onto_eye(shell_mesh, eyeball_mesh, verts, eye_mid_verts, 0.05)

    # snap shell border
    # snap_eye_shell_border()
    blend_points(
        shell_blend_mesh, shell_mesh, EYE_SHELL_BORDER_VERTS + EYE_SHELL_BLEND_VERTS
    )

    blend_vertices = [
        "{}.vtx[{}]".format(shell_mesh, i) for i in EYE_SHELL_BLEND_VERTS
    ]

    cmds.polyAverageVertex(blend_vertices, i=10, ch=False)

    # smooth corners
    corner_verts = [
        "{}.vtx[{}]".format(shell_mesh, i)
        for i in L_EYE_SHELL_CORNER_VERTS + R_EYE_SHELL_CORNER_VERTS
    ]

    cmds.polyAverageVertex(corner_verts, i=10, ch=False)
    cmds.polyAverageVertex(corner_verts, i=10, ch=False)

    # smooth whole mesh except borders
    shell_mush = cmds.deltaMush(shell_mesh, smoothingIterations=2)[0]
    cmds.setAttr("{}.displacement".format(shell_mush), 0.0)

    # clean up eye edge
    cmds.select(edge_mesh)
    cmds.DeleteHistory()

    for eyeball_mesh, inner_verts, blend_verts, eye_mid_verts in [
        (l_eyeball_mesh, L_EDGE_INNER_VERTS, L_EDGE_BLEND_VERTS, L_EYE_MID_VERTS),
        (r_eyeball_mesh, R_EDGE_INNER_VERTS, R_EDGE_BLEND_VERTS, R_EYE_MID_VERTS),
    ]:
        project_mesh_onto_eye(edge_mesh, eyeball_mesh, inner_verts + blend_verts, eye_mid_verts, 0.01)
        # snap_eye_edge(eyeball_mesh, edge_mesh, inner_verts, blend_verts)

    blend_points(
        edge_blend_mesh, edge_mesh, EDGE_BORDER_VERTS
    )

    edge_mush = cmds.deltaMush(edge_mesh, smoothingIterations=5)[0]
    cmds.setAttr("{}.displacement".format(edge_mush), 0.0)

    return True

def transfer_face_meshes(
        src_prefix="src_",
        dst_head_mesh="head_lod0_mesh",
        l_eyeball_mesh="eyeLeft_lod0_mesh",
        r_eyeball_mesh="eyeRight_lod0_mesh",
        cartilage_mesh="cartilage_lod0_mesh",
        edge_mesh="eyeEdge_lod0_mesh",
        shell_mesh="eyeshell_lod0_mesh",
        lash_mesh="eyelashes_lod0_mesh",
        transfer_eyeballs=True,
        transfer_eyelashes=True,
        transfer_eyewet=True,
        transfer_inner_mouth=True,
        # recalculate_pivots=True,
        cleanup=True,
):
    """
    duplicate wrapper mesh
    duplicate head mesh
    wrap wrapper mesh to new head mesh
    wrap other meshes to new wrapper mesh plus delta mush
    blendshape head mesh to dst head
    get scale difference between wrapper meshes and point delta for vertex 0
    transform scale eyeball mesh and offset by delta

    recalculate_pivots:
        correct for eyelid angle by getting relationship of eye pivot with average eyelid edge points

    eye shell approach:
        create closed wrapper mesh from cone wrapper
        wrap shell mesh to closed wrapper
        duplicate shell and wrap to head
        blend outer edge of shell to duplicated shell
        project inner section onto eye with offset
        average corners
        delta mush without displacement to relax whole mesh slightly (minus border edges)

    eye edge approach:
        duplicate as "blend mesh" and wrap to head
        wrap to shell
        project inner loops onto eyeball
        fix outer border by matching to blend mesh
        delta mush without displacement to relax whole mesh slightly (minus border edges)


    TODO check how corner of edge is getting messed up

    TODO test with shaders and motion

    TODO test on another asset


from . import mhFaceMeshes

mhFaceMeshes.transfer_eye_meshes(
    "l_eyelid_wrapper_mesh", "r_eyelid_wrapper_mesh", ["eyeshell_lod0_mesh", "eyelashes_lod0_mesh"]
)

    TODO test new methodology!!!

    """

    src_head_mesh = "{}{}".format(src_prefix, dst_head_mesh)
    l_src_eyeball_mesh = "{}{}".format(src_prefix, l_eyeball_mesh)
    r_src_eyeball_mesh = "{}{}".format(src_prefix, r_eyeball_mesh)

    all_meshes = []

    # validate options
    if not cmds.objExists(dst_head_mesh):
        raise mhCore.MHError("destination head not found: {}".format(dst_head_mesh))

    if all([
        transfer_eyewet,
        not cmds.objExists(l_eyeball_mesh),
        not transfer_eyeballs
    ]):
        raise mhCore.MHError("Cannot create eyewet without eyeball meshes")

    # create group
    transfer_grp = cmds.createNode("transform", name="transfer_GRP")

    # create src wrapper meshes
    l_src_wrapper_mesh, r_src_wrapper_mesh = create_eyelid_wrapper_meshes(
        src_head_mesh, l_src_eyeball_mesh, r_src_eyeball_mesh, scale=1.0, prefix="src_"
    )

    cmds.parent(l_src_wrapper_mesh, r_src_wrapper_mesh, transfer_grp)

    # get head points
    src_points = mhMayaUtils.get_points(src_head_mesh, as_vector=True)
    dst_points = mhMayaUtils.get_points(dst_head_mesh, as_vector=True)

    # get eyelid edge points
    l_eyelid_vert_ids = mhMayaUtils.edges_to_vertex_ids(src_head_mesh, L_EYELID_EDGES)
    r_eyelid_vert_ids = mhMayaUtils.edges_to_vertex_ids(src_head_mesh, R_EYELID_EDGES)

    l_src_eyelid_points = [src_points[i] for i in l_eyelid_vert_ids]
    r_src_eyelid_points = [src_points[i] for i in r_eyelid_vert_ids]
    l_dst_eyelid_points = [dst_points[i] for i in l_eyelid_vert_ids]
    r_dst_eyelid_points = [dst_points[i] for i in r_eyelid_vert_ids]

    # approximate dst eyeball scale based on width
    l_src_x = [i.x for i in l_src_eyelid_points]
    l_dst_x = [i.x for i in l_dst_eyelid_points]
    r_src_x = [i.x for i in r_src_eyelid_points]
    r_dst_x = [i.x for i in r_dst_eyelid_points]

    l_src_width = max(l_src_x) - min(l_src_x)
    l_dst_width = max(l_dst_x) - min(l_dst_x)
    r_src_width = max(r_src_x) - min(r_src_x)
    r_dst_width = max(r_dst_x) - min(r_dst_x)

    l_eyeball_scale = l_dst_width / l_src_width
    r_eyeball_scale = r_dst_width / r_src_width

    dst_eyeball_scale = (l_eyeball_scale + r_eyeball_scale)/2.0

    # determine l dst pivot
    l_src_wrapper_points = mhMayaUtils.get_points(l_src_wrapper_mesh, as_vector=True)
    l_src_eye_pivot = l_src_wrapper_points[0]
    l_src_eyelid_avg_point = mhMayaUtils.get_average_position(l_src_eyelid_points)
    l_dst_eyelid_avg_point = mhMayaUtils.get_average_position(l_dst_eyelid_points)
    l_src_eye_pivot_delta = [a - b for a, b in zip(l_src_eye_pivot, l_src_eyelid_avg_point)]

    l_dst_eye_pivot = [
        (a * dst_eyeball_scale) + b for a, b in zip(l_src_eye_pivot_delta, l_dst_eyelid_avg_point)
    ]

    # determine r dst pivot
    r_src_wrapper_points = mhMayaUtils.get_points(r_src_wrapper_mesh, as_vector=True)
    r_src_eye_pivot = r_src_wrapper_points[0]
    r_src_eyelid_avg_point = mhMayaUtils.get_average_position(r_src_eyelid_points)
    r_dst_eyelid_avg_point = mhMayaUtils.get_average_position(r_dst_eyelid_points)
    r_src_eye_pivot_delta = [a - b for a, b in zip(r_src_eye_pivot, r_src_eyelid_avg_point)]

    r_dst_eye_pivot = [
        (a * dst_eyeball_scale) + b for a, b in zip(r_src_eye_pivot_delta, r_dst_eyelid_avg_point)
    ]

    # create dst wrapper meshes
    l_dst_wrapper_mesh, r_dst_wrapper_mesh = create_eyelid_wrapper_meshes(
        dst_head_mesh, l_dst_eye_pivot, r_dst_eye_pivot, scale=1.0, prefix="dst_"
    )

    cmds.parent(l_dst_wrapper_mesh, r_dst_wrapper_mesh, transfer_grp)

    # create driver meshes
    blend_head = cmds.duplicate(src_head_mesh, name="head_blend_mesh")[0]
    cmds.parent(blend_head, transfer_grp)

    temp = cmds.duplicate(l_src_wrapper_mesh, r_src_wrapper_mesh)
    src_wrapper_mesh = cmds.polyUnite(temp, name="src_eyelid_wrapper_mesh", constructionHistory=False)[0]

    temp = cmds.duplicate(l_dst_wrapper_mesh, r_dst_wrapper_mesh)
    dst_wrapper_mesh = cmds.polyUnite(temp, name="dst_eyelid_wrapper_mesh", constructionHistory=False)[0]

    cmds.parent(src_wrapper_mesh, dst_wrapper_mesh, transfer_grp)

    # l_orig_wrapper = cmds.duplicate(l_src_wrapper_mesh, name="{}_orig".format(l_src_wrapper_mesh))[0]
    # r_orig_wrapper = cmds.duplicate(r_src_wrapper_mesh, name="{}_orig".format(r_src_wrapper_mesh))[0]

    # wrap l/r wrapper meshes to combined wrapper mesh
    mhMayaUtils.create_wrap(
        [l_src_wrapper_mesh, ],
        src_wrapper_mesh,
        attrs={"exclusiveBind": True}
    )

    # create closed wrapper mesh
    closed_wrapper_meshes = []

    for node in l_src_wrapper_mesh, r_src_wrapper_mesh:
        closed_mesh = cmds.duplicate(node)[0]
        cmds.polyCloseBorder(closed_mesh, ch=False)
        cmds.polyTriangulate(closed_mesh, ch=False)
        cmds.delete("{}.f[0:59]".format(closed_mesh))
        closed_wrapper_meshes.append(closed_mesh)

    closed_wrapper_mesh = cmds.polyUnite(
        closed_wrapper_meshes, name="eyelid_closedWrapper_mesh", constructionHistory=False
    )[0]

    cmds.parent(closed_wrapper_mesh, transfer_grp)

    # wrap closed wrapper to src wrapper mesh
    mhMayaUtils.create_wrap(
        closed_wrapper_mesh,
        src_wrapper_mesh,
        attrs={"exclusiveBind": True}
    )

    # inner mouth
    if transfer_inner_mouth:
        all_meshes += create_inner_mouth_meshes(blend_head)

    # eyewet meshes and deformers
    if transfer_eyewet:
        meshes, edge_blend_mesh, shell_blend_mesh = create_eyewet_meshes(
            cartilage_mesh, edge_mesh, shell_mesh, transfer_grp, blend_head, closed_wrapper_mesh,
            src_prefix=src_prefix
        )

        all_meshes += meshes
    else:
        edge_blend_mesh = shell_blend_mesh = None


    # eyelashes
    if transfer_eyelashes:
        src_lash_mesh = "{}{}".format(src_prefix, lash_mesh)
        cmds.duplicate(src_lash_mesh, name=lash_mesh)
        cmds.parent(lash_mesh, world=True)

        mhMayaUtils.create_wrap(
            lash_mesh,
            src_wrapper_mesh,
            attrs={
                "exclusiveBind": False,
                # weightThreshold=0,
                # maxDistance=0.0,
                # autoWeightThreshold=False,
                # falloffMode=0
            }
        )

        lash_mush = cmds.deltaMush(lash_mesh)

        all_meshes += [lash_mesh]

    # turn on blendshapes
    head_bs_node = cmds.blendShape(dst_head_mesh, blend_head)[0]
    cmds.setAttr("{}.w[0]".format(head_bs_node), 1.0)

    wrapper_bs_node = cmds.blendShape(dst_wrapper_mesh, src_wrapper_mesh)[0]
    cmds.setAttr("{}.w[0]".format(wrapper_bs_node), 1.0)

    # delete history on wrap meshes
    # cmds.select(l_src_wrapper_mesh, r_src_wrapper_mesh)
    # cmds.DeleteHistory()

    # transfer eyes
    if transfer_eyeballs:
        # transfer_eyeball_meshes(
        #     l_eyeball_mesh, r_eyeball_mesh, l_src_wrapper_mesh, r_src_wrapper_mesh, l_orig_wrapper, r_orig_wrapper,
        #     src_prefix=src_prefix, recalculate_pivots=recalculate_pivots,
        # )

        transfer_eyeball_mesh(
            l_eyeball_mesh, l_src_eye_pivot, l_dst_eye_pivot, dst_eyeball_scale, src_prefix="src_",
        )

        transfer_eyeball_mesh(
            r_eyeball_mesh, r_src_eye_pivot, r_dst_eye_pivot, dst_eyeball_scale, src_prefix="src_",
        )

        all_meshes += [l_eyeball_mesh, r_eyeball_mesh]

    # eyewet post
    if transfer_eyewet:
        eyewet_post(edge_mesh, edge_blend_mesh, shell_mesh, shell_blend_mesh, l_eyeball_mesh, r_eyeball_mesh)

    # cleanup
    if cleanup:
        meshes = [
            i for i in all_meshes
            if cmds.objExists(i)
        ]

        cmds.select(meshes)
        cmds.DeleteHistory()

        cmds.delete(transfer_grp)

        for node in ["eyeshell_lod0_meshBase", "teeth_lod0_meshBase"]:
            if cmds.objExists(node):
                cmds.delete(node)

    return True
