# brenmeta
metahuman tools


# Notes on commands:

# SetVertexPositionsCommand
used to change vertex positions values.

SetVertexPositionsCommand(meshIndex, positions, operation)
SetVertexPositionsCommand(meshIndex, xs, ys, zs, operation)
SetVertexPositionsCommand(meshIndex, positions, masks, operation)
SetVertexPositionsCommand(meshIndex, xs, ys, zs, masks, operation)

# SetBlendShapeTargetDeltasCommand
used to change blend shape target deltas.

SetBlendShapeTargetDeltasCommand(meshIndex, blendShapeTargetIndex, deltas, vertexIndices, operation)
SetBlendShapeTargetDeltasCommand(meshIndex, blendShapeTargetIndex, xs, ys, zs, vertexIndices, operation)
SetBlendShapeTargetDeltasCommand(meshIndex, blendShapeTargetIndex, deltas, vertexIndices, masks, operation)
SetBlendShapeTargetDeltasCommand(meshIndex, blendShapeTargetIndex, xs, ys, zs, vertexIndices, masks, operation)


# ScaleCommand
used to scale neutral joints, vertex positions and joint and blendshape deltas by a factor.

Note: Only translation attributes of neutral joints and joint deltas are scaled.

ScaleCommand(float scale, Vector3 origin)

