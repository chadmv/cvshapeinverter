cvshapeinverter
===============

A script and deformer that can invert a shape through a deformation chain so the shape can be applied as a front of chain shape. This has the same functionality as Christian Breitling’s correctiveShape plug-in. He stopped providing it after Maya 2008 so I’m providing a Python version that doesn’t need to be compiled.

Installation:
-------------
Copy cvshapeinverter.txt into your maya/modules folder.
Edit the copied cvshapeinverter.txt with the path to the cvshapeinverter folder.

Usage:
------

Pose your skinned model in the pose that you want to correct. Duplicate the mesh and sculpt in your fixes. Select the original skinned model, shift select the corrected model and run:

```
import cvshapeinverter
cvshapeinverter.invert()
```

An inverted shape will be generated which you can then apply as a front of chain blendShape target. The generated shape will have a live deformer affecting it so edits you make on your corrected mesh will be inverted through the deformer.

Notes:
------
The mesh should not have any absolute deformations in the deformation chain.  This includes
blendShapes that still have the targets connected.
