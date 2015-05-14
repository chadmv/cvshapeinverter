"""@brief Inverts a shape through the deformation chain
@author Chad Vernon - chadvernon@gmail.com - www.chadvernon.com
"""

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import math


def invert(base=None, corrective=None, name=None):
    """@brief Inverts a shape through the deformation chain.

    @param[in] base Deformed base mesh.
    @param[in] corrective Sculpted corrective mesh.
    @param[in] name Name of the generated inverted shape.
    @return The name of the inverted shape.
    """
    if not cmds.pluginInfo('cvShapeInverter.py', query=True, loaded=True):
        cmds.loadPlugin('cvShapeInverter.py')
    if not base or not corrective:
        sel = cmds.ls(sl=True)
        if not sel or len(sel) != 2:
            cmds.undoInfo(closeChunk=True)
            raise RuntimeError, 'Select base then corrective'
        base, corrective = sel

    # Get points on base mesh
    basePoints = getPoints(base)
    numPoints = basePoints.length()

    # Get points on corrective mesh
    correctivePoints = getPoints(corrective)

    # Get the intermediate mesh
    shapes = cmds.listRelatives(base, children=True, shapes=True)
    for s in shapes:
        if cmds.getAttr('%s.intermediateObject' % s) and cmds.listConnections('%s.worldMesh' % s,
                source=False):
            origMesh = s
            break
    else:
        raise RuntimeError('No intermediate shape found for %s.' % base)

    # Get the component offset axes
    origPoints = getPoints(origMesh)
    xPoints = OpenMaya.MPointArray(origPoints)
    yPoints = OpenMaya.MPointArray(origPoints)
    zPoints = OpenMaya.MPointArray(origPoints)

    cmds.undoInfo(openChunk=True)
    for i in range(numPoints):
        xPoints[i].x += 1.0
        yPoints[i].y += 1.0
        zPoints[i].z += 1.0
    setPoints(origMesh, xPoints)
    xPoints = getPoints(base)
    setPoints(origMesh, yPoints)
    yPoints = getPoints(base)
    setPoints(origMesh, zPoints)
    zPoints = getPoints(base)
    setPoints(origMesh, origPoints)

    # Create the mesh to get the inversion deformer
    if not name:
        name = '%s_inverted' % corrective

    invertedShape = cmds.duplicate(base, name=name)[0]
    # Delete the unnessary shapes
    shapes = cmds.listRelatives(invertedShape, children=True, shapes=True, path=True)
    for s in shapes:
        if cmds.getAttr('%s.intermediateObject' % s):
            cmds.delete(s)
    setPoints(invertedShape, origPoints)
    # Unlock the transformation attrs
    for attr in 'trs':
        for x in 'xyz':
            cmds.setAttr('%s.%s%s' % (invertedShape, attr, x), lock=False)
    cmds.setAttr('%s.visibility' % invertedShape, 1)
    deformer = cmds.deformer(invertedShape, type='cvShapeInverter')[0]

    # Calculate the inversion matrices
    oDeformer = getMObject(deformer)
    fnDeformer = OpenMaya.MFnDependencyNode(oDeformer)
    plugMatrix = fnDeformer.findPlug('inversionMatrix', False)
    fnMatrixData = OpenMaya.MFnMatrixData()
    for i in range(numPoints):
        matrix = OpenMaya.MMatrix()
        setMatrixRow(matrix, xPoints[i] - basePoints[i], 0)
        setMatrixRow(matrix, yPoints[i] - basePoints[i], 1)
        setMatrixRow(matrix, zPoints[i] - basePoints[i], 2)
        matrix = matrix.inverse()
        oMatrix = fnMatrixData.create(matrix)

        plugMatrixElement = plugMatrix.elementByLogicalIndex(i)
        plugMatrixElement.setMObject(oMatrix)

    # Store the base points.
    fnPointData = OpenMaya.MFnPointArrayData()
    oPointData = fnPointData.create(basePoints)
    plugDeformedPoints = fnDeformer.findPlug('deformedPoints', False)
    plugDeformedPoints.setMObject(oPointData)

    cmds.connectAttr('%s.outMesh' % getShape(corrective), '%s.correctiveMesh' % deformer)
    cmds.setAttr('%s.activate' % deformer, True)

    cmds.undoInfo(closeChunk=True)
    return invertedShape


def getShape(node):
    """@brief Returns a shape node from a given transform or shape.

    @param[in] node Name of the node.
    @return The associated shape node.
    """
    if cmds.nodeType(node) == 'transform':
        shapes = cmds.listRelatives(node, shapes=True, path=True)
        if not shapes:
            raise RuntimeError, '%s has no shape' % node
        return shapes[0]
    elif cmds.nodeType(node) in ['mesh', 'nurbsCurve', 'nurbsSurface']:
        return node


def getMObject(node):
    """@brief Gets the dag path of a node.

    @param[in] node Name of the node.
    @return The dag path of a node.
    """
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    oNode = OpenMaya.MObject()
    selectionList.getDependNode(0, oNode)
    return oNode


def getDagPath(node):
    """@brief Gets the dag path of a node.

    @param[in] node Name of the node.
    @return The dag path of a node.
    """
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    pathNode = OpenMaya.MDagPath()
    selectionList.getDagPath(0, pathNode)
    return pathNode


def getPoints(path, space=OpenMaya.MSpace.kObject):
    """@brief Get the control point positions of a geometry node.

    @param[in] path Name or dag path of a node.
    @param[in] space Space to get the points.
    @return The MPointArray of points.
    """
    if isinstance(path, str) or isinstance(path, unicode):
        path = getDagPath(getShape(path))
    itGeo = OpenMaya.MItGeometry(path)
    points = OpenMaya.MPointArray()
    itGeo.allPositions(points, space)
    return points


def setPoints(path, points, space=OpenMaya.MSpace.kObject):
    """@brief Set the control points positions of a geometry node.

    @param[in] path Name or dag path of a node.
    @param[in] points MPointArray of points.
    @param[in] space Space to get the points.
    """
    if isinstance(path, str) or isinstance(path, unicode):
        path = getDagPath(getShape(path))
    itGeo = OpenMaya.MItGeometry(path)
    itGeo.setAllPositions(points, space)


def setMatrixRow(matrix, newVector, row):
    """@brief Sets a matrix row with an MVector or MPoint.

    @param[in/out] matrix Matrix to set.
    @param[in] newVector Vector to use.
    @param[in] row Row number.
    """
    setMatrixCell(matrix, newVector.x, row, 0)
    setMatrixCell(matrix, newVector.y, row, 1)
    setMatrixCell(matrix, newVector.z, row, 2)


def setMatrixCell(matrix, value, row, column):
    """@brief Sets a matrix cell

    @param[in/out] matrix Matrix to set.
    @param[in] value Value to set cell.
    @param[in] row Row number.
    @param[in] column Column number.
    """
    OpenMaya.MScriptUtil.setDoubleArray(matrix[row], column, value)

