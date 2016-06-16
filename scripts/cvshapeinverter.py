"""@brief Inverts a shape through the deformation chain
@author Chad Vernon - chadvernon@gmail.com - www.chadvernon.com

Example usage:

Pose your skinned model in the pose that you want to correct.
Duplicate the mesh and sculpt in your fixes. Select the original skinned model,
shift select the corrected model and run:

import cvshapeinverter
cvshapeinverter.invert()

An inverted shape will be generated which you can then apply as a front of chain blendShape target.
The generated shape will have a live deformer affecting it so edits you make on your corrected mesh
will be inverted through the deformer.
"""

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import math


def invert(base=None, corrective=None, name=None):
    """Inverts a shape through the deformation chain.

    @param[in] base Deformed base mesh.
    @param[in] corrective Sculpted corrective mesh.
    @param[in] name Name of the generated inverted shape.
    @return The name of the inverted shape.
    """
    cmds.loadPlugin('cvshapeinverter_plugin.py', qt=True)
    if not base or not corrective:
        sel = cmds.ls(sl=True)
        if not sel or len(sel) != 2:
            cmds.undoInfo(closeChunk=True)
            raise RuntimeError, 'Select base then corrective'
        base, corrective = sel

    # Get points on base mesh
    base_points = get_points(base)
    point_count = base_points.length()

    # Get points on corrective mesh
    corrective_points = get_points(corrective)

    # Get the intermediate mesh
    orig_mesh = get_shape(base, intermediate=True)

    # Get the component offset axes
    orig_points = get_points(orig_mesh)
    x_points = OpenMaya.MPointArray(orig_points)
    y_points = OpenMaya.MPointArray(orig_points)
    z_points = OpenMaya.MPointArray(orig_points)

    cmds.undoInfo(openChunk=True)
    for i in range(point_count):
        x_points[i].x += 1.0
        y_points[i].y += 1.0
        z_points[i].z += 1.0
    set_points(orig_mesh, x_points)
    x_points = get_points(base)
    set_points(orig_mesh, y_points)
    y_points = get_points(base)
    set_points(orig_mesh, z_points)
    z_points = get_points(base)
    set_points(orig_mesh, orig_points)

    # Create the mesh to get the inversion deformer
    if not name:
        name = '%s_inverted' % corrective

    inverted_shapes = cmds.duplicate(base, name=name)[0]
    # Delete the unnessary shapes
    shapes = cmds.listRelatives(inverted_shapes, children=True, shapes=True, path=True)
    for s in shapes:
        if cmds.getAttr('%s.intermediateObject' % s):
            cmds.delete(s)
    set_points(inverted_shapes, orig_points)
    # Unlock the transformation attrs
    for attr in 'trs':
        for x in 'xyz':
            cmds.setAttr('%s.%s%s' % (inverted_shapes, attr, x), lock=False)
    cmds.setAttr('%s.visibility' % inverted_shapes, 1)
    deformer = cmds.deformer(inverted_shapes, type='cvShapeInverter')[0]

    # Calculate the inversion matrices
    deformer_mobj = get_mobject(deformer)
    fn_deformer = OpenMaya.MFnDependencyNode(deformer_mobj)
    plug_matrix = fn_deformer.findPlug('inversionMatrix', False)
    fn_matrix_data = OpenMaya.MFnMatrixData()
    for i in range(point_count):
        matrix = OpenMaya.MMatrix()
        set_matrix_row(matrix, x_points[i] - base_points[i], 0)
        set_matrix_row(matrix, y_points[i] - base_points[i], 1)
        set_matrix_row(matrix, z_points[i] - base_points[i], 2)
        set_matrix_row(matrix, corrective_points[i], 3)
        matrix = matrix.inverse()
        matrix_mobj = fn_matrix_data.create(matrix)

        plug_matrixElement = plug_matrix.elementByLogicalIndex(i)
        plug_matrixElement.setMObject(matrix_mobj)

    # Store the base points.
    fn_point_data = OpenMaya.MFnPointArrayData()
    point_data_mobj = fn_point_data.create(base_points)
    plug_deformed_points = fn_deformer.findPlug('deformedPoints', False)
    plug_deformed_points.setMObject(point_data_mobj)

    cmds.connectAttr('%s.outMesh' % get_shape(corrective), '%s.correctiveMesh' % deformer)

    cmds.undoInfo(closeChunk=True)
    return inverted_shapes


def get_shape(node, intermediate=False):
    """Returns a shape node from a given transform or shape.

    @param[in] node Name of the node.
    @param[in] intermediate True to get the intermediate mesh
    @return The associated shape node.
    """
    if cmds.nodeType(node) == 'transform':
        shapes = cmds.listRelatives(node, shapes=True, path=True)
        if not shapes:
            raise RuntimeError, '%s has no shape' % node
        for shape in shapes:
            is_intermediate = cmds.getAttr('%s.intermediateObject' % shape)
            if intermediate and is_intermediate and cmds.listConnections('%s.worldMesh' % shape,
                                                                         source=False):
                return shape
            elif not intermediate and not is_intermediate:
                return shape
        raise RuntimeError('Could not find shape on node {0}'.format(node))
    elif cmds.nodeType(node) in ['mesh', 'nurbsCurve', 'nurbsSurface']:
        return node


def get_mobject(node):
    """Gets the dag path of a node.

    @param[in] node Name of the node.
    @return The dag path of a node.
    """
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(node)
    node_mobj = OpenMaya.MObject()
    selection_list.getDependNode(0, node_mobj)
    return node_mobj


def get_dag_path(node):
    """Gets the dag path of a node.

    @param[in] node Name of the node.
    @return The dag path of a node.
    """
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(node)
    path_node = OpenMaya.MDagPath()
    selection_list.getDagPath(0, path_node)
    return path_node


def get_points(path, space=OpenMaya.MSpace.kObject):
    """Get the control point positions of a geometry node.

    @param[in] path Name or dag path of a node.
    @param[in] space Space to get the points.
    @return The MPointArray of points.
    """
    if isinstance(path, basestring):
        path = get_dag_path(get_shape(path))
    it_geo = OpenMaya.MItGeometry(path)
    points = OpenMaya.MPointArray()
    it_geo.allPositions(points, space)
    return points


def set_points(path, points, space=OpenMaya.MSpace.kObject):
    """Set the control points positions of a geometry node.

    @param[in] path Name or dag path of a node.
    @param[in] points MPointArray of points.
    @param[in] space Space to get the points.
    """
    if isinstance(path, str) or isinstance(path, unicode):
        path = get_dag_path(get_shape(path))
    it_geo = OpenMaya.MItGeometry(path)
    it_geo.setAllPositions(points, space)


def set_matrix_row(matrix, new_vector, row):
    """Sets a matrix row with an MVector or MPoint.

    @param[in/out] matrix Matrix to set.
    @param[in] new_vector Vector to use.
    @param[in] row Row number.
    """
    set_matrix_cell(matrix, new_vector.x, row, 0)
    set_matrix_cell(matrix, new_vector.y, row, 1)
    set_matrix_cell(matrix, new_vector.z, row, 2)


def set_matrix_cell(matrix, value, row, column):
    """Sets a matrix cell

    @param[in/out] matrix Matrix to set.
    @param[in] value Value to set cell.
    @param[in] row Row number.
    @param[in] column Column number.
    """
    OpenMaya.MScriptUtil.setDoubleArray(matrix[row], column, value)

