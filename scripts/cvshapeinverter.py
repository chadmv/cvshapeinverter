# 
# Copyright (c) 2011 Chad Vernon
# 

## @brief Inverts a shape through the deformation chain
# @author Chad Vernon - chadvernon@gmail.com - www.chadvernon.com
#


import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import math


## @brief Inverts a shape through the deformation chain.
#
# @param[in] base Deformed base mesh.
# @param[in] corrective Sculpted corrective mesh.
# @param[in] name Name of the generated inverted shape.
#
# @return The name of the inverted shape.
#
def invert(base=None, corrective=None, name=None):
    if not cmds.pluginInfo('cvShapeInverter.py', query=True, loaded=True):
        cmds.loadPlugin('cvShapeInverter.py')
    # end if
    cmds.undoInfo(openChunk=True)
    if not base or not corrective:
        sel = cmds.ls(sl=True)
        if not sel or len(sel) != 2:
            cmds.undoInfo(closeChunk=True)
            raise RuntimeError, 'Select base then corrective'
        # end if
        base, corrective = sel
    # end if
    
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
        # end if
    else:
        cmds.undoInfo(closeChunk=True)
        raise RuntimeError('No intermediate shape found for %s.' % base)
    # end for


    # Get the component offset axes
    origPoints = getPoints(origMesh)
    xPoints = OpenMaya.MPointArray(origPoints)
    yPoints = OpenMaya.MPointArray(origPoints)
    zPoints = OpenMaya.MPointArray(origPoints)
    
    for i in range(numPoints):
        xPoints[i].x += 1.0
        yPoints[i].y += 1.0
        zPoints[i].z += 1.0
    # end for
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
    # end if
    
    invertedShape = cmds.duplicate(base, name=name)[0]
    # Delete the unnessary shapes
    shapes = cmds.listRelatives(invertedShape, children=True, shapes=True)
    for s in shapes:
        if cmds.getAttr('%s.intermediateObject' % s):
            cmds.delete(s)
        # end if
    # end for
    setPoints(invertedShape, origPoints)
    # Unlock the transformation attrs
    for attr in 'trs':
        for x in 'xyz':
            cmds.setAttr('%s.%s%s' % (invertedShape, attr, x), lock=False)
        # end for
    # end for
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
    # end for


    # Store the base points.
    fnPointData = OpenMaya.MFnPointArrayData()
    oPointData = fnPointData.create(basePoints)
    plugDeformedPoints = fnDeformer.findPlug('deformedPoints', False)
    plugDeformedPoints.setMObject(oPointData)

    cmds.connectAttr('%s.outMesh' % getShape(corrective), '%s.correctiveMesh' % deformer)
    cmds.setAttr('%s.activate' % deformer, True)

    cmds.undoInfo(closeChunk=True)
    
    return invertedShape
# end invert

## @brief Returns a shape node from a given transform or shape.
#
# @param[in] node Name of the node.
#
# @return The associated shape node.
#
def getShape(node):
    if cmds.nodeType(node) == 'transform':
        shapes = cmds.listRelatives(node, shapes=True)
        if not shapes:
            raise RuntimeError, '%s has no shape' % node
        # end if
        return shapes[0]
    elif cmds.nodeType(node) in ['mesh', 'nurbsCurve', 'nurbsSurface']:
        return node
    # end if
# end getShape


## @brief Gets the dag path of a node.
#
# @param[in] node Name of the node.
#
# @return The dag path of a node.
#
def getMObject(node):
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    oNode = OpenMaya.MObject()
    selectionList.getDependNode(0, oNode)
    return oNode
# end getMObject


## @brief Gets the dag path of a node.
#
# @param[in] node Name of the node.
#
# @return The dag path of a node.
#
def getDagPath(node):
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    pathNode = OpenMaya.MDagPath()
    selectionList.getDagPath(0, pathNode)
    return pathNode
# end getDagPath


## @brief Get the control point positions of a geometry node.
#
# @param[in] path Name or dag path of a node.
# @param[in] space Space to get the points.
#
# @return The MPointArray of points.
#
def getPoints(path, space=OpenMaya.MSpace.kObject):
    if isinstance(path, str) or isinstance(path, unicode):
        path = getDagPath(getShape(path))
    # end if
    itGeo = OpenMaya.MItGeometry(path)
    points = OpenMaya.MPointArray()
    itGeo.allPositions(points, space)
    return points
# end getPoints


## @brief Set the control points positions of a geometry node.
#
# @param[in] path Name or dag path of a node.
# @param[in] points MPointArray of points.
# @param[in] space Space to get the points.
#
def setPoints(path, points, space=OpenMaya.MSpace.kObject):
    if isinstance(path, str) or isinstance(path, unicode):
        path = getDagPath(getShape(path))
    # end if
    itGeo = OpenMaya.MItGeometry(path)
    itGeo.setAllPositions(points, space)
# end setPoints


## @brief Sets a matrix row with an MVector or MPoint.
#
# @param[in/out] matrix Matrix to set.
# @param[in] newVector Vector to use.
# @param[in] row Row number.
#
def setMatrixRow(matrix, newVector, row):
    setMatrixCell(matrix, newVector.x, row, 0)
    setMatrixCell(matrix, newVector.y, row, 1)
    setMatrixCell(matrix, newVector.z, row, 2)
# end setMatrixRow


## @brief Sets a matrix cell
#
# @param[in/out] matrix Matrix to set.
# @param[in] newVector Vector to use.
# @param[in] row Row number.
# @param[in] column Column number.
#
def setMatrixCell(matrix, value, row, column):
    OpenMaya.MScriptUtil.setDoubleArray(matrix[row], column, value)
# end setMatrixCell

