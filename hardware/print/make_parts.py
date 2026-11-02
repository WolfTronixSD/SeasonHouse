"""Printable parts for the Corner Spider winch, built with manifold3d.

    pip install manifold3d trimesh numpy
    python3 hardware/print/make_parts.py

Writes winch_bracket.stl, winch_spool.stl and spider_body.stl next to this
script, each already lying in its print orientation. All sizes are in mm.
"""
import math
import os

import numpy as np
import trimesh
import manifold3d
from manifold3d import CrossSection, Manifold

OUT = os.path.dirname(os.path.abspath(__file__))
SEG = 72  # circle segments

# ---- NEMA17 (STEPPERONLINE 17HS15-1504S: 42.3 mm square, 31 mm hole spacing,
# 22 mm boss, 5 mm D-shaft sticking out 24 mm)
NEMA_HOLE = 31.0
NEMA_BOSS = 22.0
SHAFT_D = 5.0
SHAFT_FLAT = 0.5

# ---- spool (the firmware's step maths assumes a 30 mm hub)
HUB_D = 30.0
FLANGE_D = 44.0


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl(r, h, r2=None):
    """Along +z from z=0."""
    return Manifold.cylinder(h, r, r if r2 is None else r2, SEG)


def along_y(m):   # turn a +z part so it points along +y
    return m.rotate((-90, 0, 0))


def along_x(m):
    return m.rotate((0, 90, 0))


def union(parts):
    return Manifold.batch_boolean(parts, manifold3d.OpType.Add)


def ball(p, r):
    return Manifold.sphere(r, 32).translate(p)


def capsule(a, b, ra, rb):
    return Manifold.batch_hull([ball(a, ra), ball(b, rb)])


def save(m, name):
    m = m.translate((0, 0, -m.bounding_box()[2]))      # sit on the bed
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)
    assert tm.is_watertight, name
    tm.export(os.path.join(OUT, name))
    lo, hi = tm.bounds
    print(f"{name}: {hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} mm, {tm.volume/1000:.1f} cm3")


# =========================================================== winch bracket ===
# Installed: the top plate screws to the ceiling (or the underside of a shelf),
# the motor hangs behind the front plate with its shaft pointing forward (+y),
# the spool sits between the top plate and the guide arm, and the line drops
# through the hole in the arm. The home microswitch bolts to the tab under the
# arm so the bead on the line lifts its lever when the spider is fully up.
T = 6.0                      # front plate thickness
ZC = -29.5                   # motor axis height under the ceiling
ARM_Z = (-61.0, -56.0)       # guide arm
SPOOL_GAP = 1.5              # spool face to front plate
LINE_X = HUB_D / 2           # the line leaves the spool on this side
SPOOL_LEN = 1.6 + 10.0 + (FLANGE_D - HUB_D) / 2 + 6.6
LINE_Y = SPOOL_GAP + SPOOL_LEN - (1.6 + 5.0)       # middle of the straight hub, installed


def bracket():
    front = box(-30, 30, -T, 0, ARM_Z[0], 0)
    top = box(-42, 42, -T, 40, -5, 0)
    arm = box(-30, 48, -T, 32, ARM_Z[0], ARM_Z[1])
    tab = box(20, 46, LINE_Y + 4, LINE_Y + 8, -88, ARM_Z[0] + 0.01)   # switch body sits in front, lever under the line
    parts = [front, top, arm, tab]
    for x0 in (-30, 26):     # gussets, outside the spool's reach
        for tri in ([(0, -21), (16, -5), (0, -5)], [(0, ARM_Z[1]), (16, ARM_Z[1]), (0, ARM_Z[1] + 16)]):
            g = Manifold.extrude(CrossSection([tri]), 4)                   # triangle in (y, z), 4 mm thick
            parts.append(g.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]]))
    b = union(parts)
    holes = []
    # motor: boss and four M3 screws, heads sunk 2.5 mm so they clear the spool
    holes.append(along_y(cyl(NEMA_BOSS / 2 + 0.6, 20)).translate((0, -T - 1, ZC)))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = (sx * NEMA_HOLE / 2, 0, ZC + sz * NEMA_HOLE / 2)
            holes.append(along_y(cyl(1.7, 20)).translate((p[0], -T - 1, p[2])))
            holes.append(along_y(cyl(3.3, 3)).translate((p[0], -2.5, p[2])))
    # the line: 3 mm hole with a funnel on top so it never rubs an edge
    holes.append(cyl(1.5, 10).translate((LINE_X, LINE_Y, ARM_Z[0] - 1)))
    holes.append(cyl(1.5, 3.01, 4.0).translate((LINE_X, LINE_Y, ARM_Z[1] - 3)))
    # ceiling screws: 4.5 mm with a countersink on the underside
    for x in (-36, 36):
        for y in (8, 32):
            holes.append(cyl(2.3, 10).translate((x, y, -8)))
            holes.append(cyl(4.6, 2.4, 2.3).translate((x, y, -5.01)))
    # microswitch slots (M2 or 2.2 mm screws, 9.5 mm apart), 12 mm of height adjustment
    for x in (33 - 4.75, 33 + 4.75):
        slot = Manifold.batch_hull([along_y(cyl(1.2, 10)).translate((x, LINE_Y, z)) for z in (-66, -79)])
        holes.append(slot)
    b = b - union(holes)
    return b.rotate((90, 0, 0))   # print lying on the front plate's back face


# ================================================================== spool ===
def spool():
    # Printed outer flange down. From the bed: outer flange, hub, a 45 degree
    # cone up to the inner flange (no supports), inner flange, set-screw collar.
    # Installed, the collar faces the bracket.
    r_hub, r_fl = HUB_D / 2, FLANGE_D / 2
    cone = r_fl - r_hub
    z_hub, z_lip = 1.6, 1.6 + 10.0 + cone           # 10 mm of straight hub for the line
    s = union([cyl(r_fl, z_hub),
               cyl(r_hub, z_lip - z_hub).translate((0, 0, z_hub)),
               cyl(r_hub, cone, r_fl).translate((0, 0, z_lip - cone)),
               cyl(r_fl, 1.6).translate((0, 0, z_lip)),
               cyl(8.0, 5.0).translate((0, 0, z_lip + 1.6))])
    top = z_lip + 6.6
    # D bore
    s = s - (cyl(SHAFT_D / 2 + 0.12, top + 2).translate((0, 0, -1)) - box(SHAFT_D / 2 - SHAFT_FLAT + 0.12, 10, -5, 5, -1, top + 2))
    # M3 set screw onto the flat, with a captive-nut slot from the top
    zc = z_lip + 1.6 + 2.5
    s = s - along_x(cyl(1.6, 12)).translate((0, 0, zc))
    s = s - box(3.3, 6.0, -3.0, 3.0, zc - 3.0, top + 1)
    # tie-off hole for the line through the outer flange, just above the hub
    s = s - cyl(0.8, 4).translate((0, r_hub + 1.6, -1))
    return s


# ================================================================= spider ===
def ellipsoid(c, r):
    return Manifold.sphere(1, 64).scale(r).translate(c)


def spider():
    ab = ellipsoid((-30, 0, 13), (34, 26, 24))
    ce = ellipsoid((14, 0, 10), (19, 17, 14))
    waist = Manifold.batch_hull([ball((-6, 0, 10), 9), ball((4, 0, 10), 9)])
    parts = [ab, ce, waist]
    # fangs
    for sy in (-1, 1):
        parts.append(capsule((28, sy * 5, 8), (36, sy * 3.5, 2.5), 2.6, 1.2))
    # legs, flat on the bed: hip, knee, tip
    for sy in (-1, 1):
        for a, bend in ((38, -32), (72, -18), (108, 18), (142, 32)):
            ar = math.radians(a)
            hip = (14 + 13 * math.cos(ar), sy * 13 * math.sin(ar), 4.0)
            knee = (hip[0] + 46 * math.cos(ar), hip[1] + sy * 46 * math.sin(ar), 3.6)
            br = math.radians(a + bend)
            tip = (knee[0] + 50 * math.cos(br), knee[1] + sy * 50 * math.sin(br), 1.8)
            parts += [capsule(hip, knee, 4.0, 3.6), capsule(knee, tip, 3.6, 1.8), ball(knee, 4.2)]
    # hanging fin over the balance point
    fin = Manifold.batch_hull([box(-22, -8, -2.5, 2.5, 22, 30), along_y(cyl(6, 5)).translate((-15, -2.5, 37))])
    parts.append(fin)
    s = union(parts)
    s = s - box(-200, 200, -200, 200, -50, 0)          # flat bottom
    cut = []
    # hollow head for the LED legs, and a 4 mm wire channel to the top
    cut.append(ellipsoid((14, 0, 11), (11, 10, 6.5)))
    cut.append(along_x(cyl(2.0, 40)).translate((-24, 0, 11)))
    cut.append(cyl(2.0, 40).translate((-24, 0, 11)))
    # 3 mm LED eyes: snug 3.1 mm holes, a recess for the 3.8 mm rim
    for sy in (-1, 1):
        d = np.array([math.cos(math.radians(12)), sy * math.sin(math.radians(18)), math.sin(math.radians(14))])
        eye = np.array([30.5, sy * 6.0, 15.0])
        rot = lambda m: m.transform(_frame(d, eye))
        cut.append(rot(cyl(1.55, 16).translate((0, 0, -14))))
        cut.append(rot(cyl(2.05, 6).translate((0, 0, -1.2))))
    # line hole through the fin
    cut.append(along_y(cyl(1.6, 20)).translate((-15, -10, 37)))
    return s - union(cut)


def _frame(d, origin):
    """3x4 transform taking +z to unit vector d, placed at origin."""
    z = d / np.linalg.norm(d)
    x = np.cross([0, 0, 1.0], z) if abs(z[2]) < 0.99 else np.array([1.0, 0, 0])
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    return np.column_stack([x, y, z, origin]).tolist()


if __name__ == "__main__":
    save(bracket(), "winch_bracket.stl")
    save(spool(), "winch_spool.stl")
    save(spider(), "spider_body.stl")
