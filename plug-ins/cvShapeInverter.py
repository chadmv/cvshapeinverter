# 
# Copyright (c) 2011 Chad Vernon
# 

import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMaya as OpenMaya
import math

class cvShapeInverter(OpenMayaMPx.MPxDeformerNode):
    kPluginNodeName = "cvShapeInverter"
    kPluginNodeId = OpenMaya.MTypeId(0x00115805)
    
    aMatrix = OpenMaya.MObject()
    aCorrectiveGeo = OpenMaya.MObject()
    aDeformedPoints = OpenMaya.MObject()
    aActivate = OpenMaya.MObject()
    
    def __init__(self):
        OpenMayaMPx.MPxDeformerNode.__init__(self)
        self.__initialized = False
        self.__matrices = []
        self.__deformedPoints = OpenMaya.MPointArray()
    # end __init__

    def deform( self, data, itGeo, localToWorldMatrix, geomIndex):
        run = data.inputValue(cvShapeInverter.aActivate).asBool()
        if not run:
            return OpenMaya.MStatus.kSuccess

        # Read the matrices
        if not self.__initialized:
            inputAttribute = OpenMayaMPx.cvar.MPxDeformerNode_input
            inputGeom = OpenMayaMPx.cvar.MPxDeformerNode_inputGeom
            hInput = data.outputArrayValue(inputAttribute)
            hInput.jumpToElement(geomIndex)
            oInputGeom = hInput.outputValue().child(inputGeom).asMesh()
            fnInputMesh = OpenMaya.MFnMesh(oInputGeom)
            numVertices = fnInputMesh.numVertices()

            hMatrix = data.inputArrayValue(cvShapeInverter.aMatrix)
            for i in range(numVertices):
                self.jumpToElement(hMatrix, i)
                self.__matrices.append(hMatrix.inputValue().asMatrix())
            # end for

            oDeformedPoints = data.inputValue(cvShapeInverter.aDeformedPoints).data()
            fnData = OpenMaya.MFnPointArrayData(oDeformedPoints)
            fnData.copyTo(self.__deformedPoints)
            self.__initialized = True
        # end if

        # Get the corrective mesh
        oMesh = data.inputValue(cvShapeInverter.aCorrectiveGeo).asMesh()
        fnMesh = OpenMaya.MFnMesh(oMesh)
        correctivePoints = OpenMaya.MPointArray()
        fnMesh.getPoints(correctivePoints)

        # Perform the inversion calculation
        while not itGeo.isDone():
            index = itGeo.index()
            delta = correctivePoints[index] - self.__deformedPoints[index]

            if (math.fabs(delta.x) < 0.001
                    and math.fabs(delta.y) < 0.001
                    and math.fabs(delta.z) < 0.001):
                itGeo.next()
                continue
            # end if

            offset = delta * self.__matrices[index]
            pt = itGeo.position() + offset
            itGeo.setPosition(pt)
            itGeo.next()
        # end while

        return OpenMaya.MStatus.kSuccess
    # end deform


    ## @brief Jumps an array handle to a logical index and uses the builder if necessary.
    #
    # @param[in/out] hArray MArrayDataHandle to jump.
    # @param[in] index Logical index.
    #
    def jumpToElement(self, hArray, index):
        try:
            hArray.jumpToElement(index)
        except:
            builder = hArray.builder()
            builder.addElement(index)
            hArray.set(builder)
            hArray.jumpToElement(index)
        # end try
    # end jumpToElement


def creator():
    return OpenMayaMPx.asMPxPtr(cvShapeInverter())
# end creator


def initialize():
    mAttr = OpenMaya.MFnMatrixAttribute()
    tAttr = OpenMaya.MFnTypedAttribute()
    nAttr = OpenMaya.MFnNumericAttribute()
    
    outputGeom = OpenMayaMPx.cvar.MPxDeformerNode_outputGeom

    cvShapeInverter.aActivate = nAttr.create('activate', 'activate',
            OpenMaya.MFnNumericData.kBoolean)
    cvShapeInverter.addAttribute(cvShapeInverter.aActivate)
    cvShapeInverter.attributeAffects(cvShapeInverter.aActivate, outputGeom)

    cvShapeInverter.aCorrectiveGeo = tAttr.create('correctiveMesh', 'cm', OpenMaya.MFnData.kMesh)
    cvShapeInverter.addAttribute(cvShapeInverter.aCorrectiveGeo)
    cvShapeInverter.attributeAffects(cvShapeInverter.aCorrectiveGeo, outputGeom)

    cvShapeInverter.aDeformedPoints = tAttr.create('deformedPoints', 'dp',
            OpenMaya.MFnData.kPointArray)
    cvShapeInverter.addAttribute(cvShapeInverter.aDeformedPoints)

    cvShapeInverter.aMatrix = mAttr.create('inversionMatrix', 'im')
    mAttr.setArray(True)
    mAttr.setUsesArrayDataBuilder(True)
    cvShapeInverter.addAttribute(cvShapeInverter.aMatrix)
# end initialize
    

def initializePlugin(mobject):
    plugin = OpenMayaMPx.MFnPlugin(mobject)
    plugin.registerNode(cvShapeInverter.kPluginNodeName, cvShapeInverter.kPluginNodeId, creator,
            initialize, OpenMayaMPx.MPxNode.kDeformerNode)
# end initializePlugin


def uninitializePlugin(mobject):
    plugin = OpenMayaMPx.MFnPlugin(mobject)
    plugin.deregisterNode(cvShapeInverter.kPluginNodeId)
# end uninitializePlugin

