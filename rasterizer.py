# 09/25/16 06:28PM
# Rasterization is computationally expensive, which is why early real-time 
# computer graphics were rendered as wireframes. It takes far less time to 
# rasterize a few lines than to fill a bunch of polygons.

# Attempt to create a rasterizer by cutting straight to the chase of NDC 
# triangles with attributes (like color).
# NDC is [-1,+1] in all dimensions

# It seems I'd probably have to iterate left-right across pixels between 
# bounds. That is, I'd pick, say, the top-most y coordinate of the triangle (in 
# screen space),

import collections
import numpy
from PIL import Image

imFilename = "triangleRasterized.png"

Vertex = collections.namedtuple('Vertex', 'x y z color')

# Draws triangles to an image
class Rasterizer:
    bgColor = (200, 200, 200)

    # imFramebuffer: PIL Image object
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.fb = [Rasterizer.bgColor for i in range(self.w*self.h)] 

        # The raster stencil is how the rasterizer determines whether or not it 
        # has already drawn a pixel. Each primitive/triangle is given its own 
        # iRaster number.
        self.rasterStencil = [0 for i in range(self.w*self.h)]
        self.iRaster = 1

    def setPixel(self, x, y, color):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.fb[y*self.w + x] = color
            self.rasterStencil[y*self.w + x] = self.iRaster

    # Horiznotal scanline-style barycentric interpolation within a triangle
    # XXX Works great when there's a large vertical distance between vertices, 
    # gives funky results otherwise
    # v is a triplet of vertices (triangle vertices)
    # vertVals is the scalars at each vertex to interpolate between
    def triIntpScanline(self, x, y, v, vertVals):
        vp = sorted(v, key=lambda a: a.y)

        # XXX Make sure point is within boundaries

        if y > vp[1]: # Use v[1] and v[2]
            horizontalLine1 = v[2].y == v[0].y
            horizontalLine2 = v[2].y == v[1].y
            t1 = (v[2].y-y) / (v[2].y-v[0].y) if not horizontalLine1 else 0
            t2 = (v[2].y-y) / (v[2].y-v[1].y) if not horizontalLine2 else 0

            valA = t1 * vertVals[0] + (1-t1)*vertVals[2]
            valB = t2 * vertVals[1] + (1-t2)*vertVals[2]
            return valA + (valB-valA)*(x-v[0].x)/(v[1].x-v[2].x)
        else: # Use v[0] and v[1]
            horizontalLine1 = v[1].y == v[0].y
            horizontalLine2 = v[2].y == v[0].y
            t1 = (y-v[0].y) / (v[1].y-v[0].y) if not horizontalLine1 else 0
            t2 = (y-v[0].y) / (v[2].y-v[0].y) if not horizontalLine2 else 0

            valA = t1 * vertVals[1] + (1-t1)*vertVals[0]
            valB = t2 * vertVals[2] + (1-t2)*vertVals[0]
            return valA + (valB-valA)*(x-v[1].x)/(v[2].x-v[1].x)

    # v0, v1 are vertex objects
    def rasterizeLine(self, v0, v1, color=None):
        color = v[0] if color is None else color
        verticalLine = (v1.x == v0.x)
        if verticalLine:
            for yPx in range(int(min(v0.y, v1.y)), max(v0.y, v1.y)+1):
                self.setPixel(v0.x, yPx, color)
            return
        else:
            m = (v1.y-v0.y)/float(v1.x-v0.x)
            
        if (abs(m) > 1):
            mp = 1/m
            dir = 1 if v1.y > v0.y else -1
            for yPx in range(int(v0.y), int(v1.y)+dir, dir):
                xPx = int(mp*(yPx-v0.y) + v0.x)
                self.setPixel(xPx, yPx, color)
        else:
            dir = 1 if v1.x > v0.x else -1
            for xPx in range(int(v0.x), int(v1.x)+dir, dir):
                yPx = int(m*(xPx-v0.x) + v0.y)
                self.setPixel(xPx, yPx, color)

    # v contains 3 vertices
    # This method works and is most elegant, but in practice it has an 
    # overly-restrictive recursion limit. You can only draw triangles with tens 
    # of pixels width before running into stack problems.
    def rasterizeTriangleFlood(self, v): #, rasterStencil):
        # Draw borders
        for i in range(3):
            self.rasterizeLine(v[i], v[(i+1)%3])

        def _floodFill(v):
            if self.rasterStencil[v.y*self.w + v.x] != self.iRaster:
                self.setPixel(v.x, v.y, v.color) # XXX interpolate color
                _floodFill(Vertex(v.x+1, v.y, v.z, v.color))
                _floodFill(Vertex(v.x-1, v.y, v.z, v.color))
                _floodFill(Vertex(v.x, v.y+1, v.z, v.color))
                _floodFill(Vertex(v.x, v.y-1, v.z, v.color))

        # Recursively fill, starting from the center
        vCenter = Vertex(
                (v[0].x + v[1].x + v[2].x)/3,
                (v[0].y + v[1].y + v[2].y)/3,
                (v[0].z + v[1].z + v[2].z)/3,
                v[0].color)
        _floodFill(vCenter)
        self.iRaster += 1

    # Renders in pixel 0's color
    def rasterizeTriangleWireframe(self, v, color=(255, 255, 255)):
        for i in range(3):
            self.rasterizeLine(v[i], v[(i+1)%3], color)

    # Recommended way to rasterize something
    # v contains 3 vertices
    # Rasterizes the triangle in two halves, split horizontally --- one top to 
    # bottom, the other bottom to top
    def rasterizeTriangleScanline(self, v):
        vp = sorted(v, key=lambda a: a.y)

        m1Vertical = vp[1].y == vp[0].y
        m2Vertical = vp[2].y == vp[0].y
        m1 = (vp[1].x-vp[0].x) / (vp[1].y-vp[0].y) if not m1Vertical else 0
        m2 = (vp[2].x-vp[0].x) / (vp[2].y-vp[0].y) if not m2Vertical else 0
        self.setPixel(vp[0].x, vp[0].y, vp[0].color)
        for yPx in range(int(vp[0].y), int(vp[1].y)+1):
            x1 = vp[0].x + m1*(yPx - vp[0].y) if not m1Vertical else vp[0].x
            x2 = vp[0].x + m2*(yPx - vp[0].y) if not m2Vertical else vp[0].x

            for xPx in range(int(min(x1,x2)), int(max(x1,x2))+1):
                r = self.triIntpScanline(xPx,yPx,v,[vx.color[0] for vx in v])
                g = self.triIntpScanline(xPx,yPx,v,[vx.color[1] for vx in v])
                b = self.triIntpScanline(xPx,yPx,v,[vx.color[2] for vx in v])
                self.setPixel(xPx, yPx, (int(r), int(g), int(b)))

        # Now iterate bottom-to-top
        m1Vertical = vp[0].y == vp[2].y
        m2Vertical = vp[1].y == vp[2].y
        m1 = (vp[0].x-vp[2].x) / (vp[0].y-vp[2].y) if not m1Vertical else 0
        m2 = (vp[1].x-vp[2].x) / (vp[1].y-vp[2].y) if not m2Vertical else 0
        self.setPixel(vp[2].x, vp[2].y, vp[2].color)
        for yPx in range(int(vp[2].y), int(vp[1].y), -1):
            x1 = vp[2].x + m1*(yPx - vp[2].y) if not m1Vertical else vp[2].x
            x2 = vp[2].x + m2*(yPx - vp[2].y) if not m2Vertical else vp[2].x

            for xPx in range(int(min(x1,x2)), int(max(x1,x2))+1):
                r = self.triIntpScanline(xPx,yPx,v,[vx.color[0] for vx in v])
                g = self.triIntpScanline(xPx,yPx,v,[vx.color[1] for vx in v])
                b = self.triIntpScanline(xPx,yPx,v,[vx.color[2] for vx in v])
                self.setPixel(xPx, yPx, (int(r), int(g), int(b)))

        self.iRaster += 1

    def save(self, imageFilename):
        im = Image.new('RGB', (self.w, self.h))
        im.putdata(self.fb)
        im.save(imageFilename)


triangleVertices = [
    Vertex(10.0, 10.0, 0.5, (255, 0, 0)),
    Vertex(40.0, 200.0, 0.5, (0, 255, 0)),
    Vertex(400.0, 230.0, 0.5, (0, 0, 255)),
]

t2Verts = [
    Vertex(2, 4, 0.5, (88, 88, 88)),
    Vertex(4, 1, 0.5, (88, 88, 88)),
    Vertex(3, 3, 0.5, (88, 88, 88)),
]

r = Rasterizer(500, 500)
# r.rasterizeTriangleFlood(triangleVertices)
r.rasterizeTriangleScanline(triangleVertices)
r.rasterizeTriangleWireframe(triangleVertices)
r.save(imFilename)