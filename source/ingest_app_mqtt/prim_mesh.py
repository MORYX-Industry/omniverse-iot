import random
from pxr import Usd, Gf, UsdGeom, Sdf, UsdShade


class PrimMesh:
    def __init__(self, path, stage: Usd.Stage):

        primObject = stage.GetPrimAtPath(path)

        if not primObject:
            raise Exception("Could load the object: " + path)

        self.mesh = stage.GetPrimAtPath(path + "/mesh")

        self._rotationIncrement = Gf.Vec3f(
            random.uniform(-1.0, 1.0) * 10.0, random.uniform(-1.0, 1.0) * 10.0, random.uniform(-1.0, 1.0) * 10.0
        )

        self._rotateXYZOp = None
        self._scale = None
        self._translate = None
        self.xform = UsdGeom.Xformable(primObject)
        for op in self.xform.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeRotateXYZ:
                self._rotateXYZOp = op
            if op.GetOpType() == UsdGeom.XformOp.TypeScale:
                self._scale = op
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                self._translate = op

        if self._rotateXYZOp is None:
            self._rotateXYZOp = self.xform.AddRotateXYZOp()
        self._rotation = Gf.Vec3f(-90.0, 180.0, 0.0)
        self._rotateXYZOp.Set(self._rotation)

    def translate(self, value: Gf.Vec3f):
        if self._translate is None:
            self._translate = self.xform.AddTranslateOp()
        self._translate.Set(value)

    def scale(self, value: Gf.Vec3f):
        if self._scale is None:
            self._scale = self.xform.AddScaleOp()
        self._scale.Set(value)

    def rotate(self):
        if abs(self._rotation[0] + self._rotationIncrement[0]) > 360.0:
            self._rotationIncrement[0] *= -1.0
        if abs(self._rotation[1] + self._rotationIncrement[1]) > 360.0:
            self._rotationIncrement[1] *= -1.0
        if abs(self._rotation[2] + self._rotationIncrement[2]) > 360.0:
            self._rotationIncrement[2] *= -1.0

        self._rotation[0] += self._rotationIncrement[0]
        self._rotation[1] += self._rotationIncrement[1]
        self._rotation[2] += self._rotationIncrement[2]
        self._rotateXYZOp.Set(self._rotation)
