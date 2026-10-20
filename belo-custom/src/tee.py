import numpy as np
from PIL import Image, ImageDraw, ImageFilter
W, H = 1400, 1600
rng = np.random.default_rng(7)

_kc = {}
def blur(a, r):
    a = np.asarray(a, np.float32)
    h, w = a.shape
    key = (h, w, r)
    if key not in _kc:
        fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.rfftfreq(w)[None, :]
        _kc[key] = np.exp(-2 * (np.pi ** 2) * (r ** 2) * (fx ** 2 + fy ** 2)).astype(np.float32)
    pad = int(min(3 * r, min(h, w) // 2))
    if pad > 0:
        ap = np.pad(a, pad, mode='edge'); hp, wp = ap.shape
        k2 = (hp, wp, r)
        if k2 not in _kc:
            fy = np.fft.fftfreq(hp)[:, None]; fx = np.fft.rfftfreq(wp)[None, :]
            _kc[k2] = np.exp(-2 * (np.pi ** 2) * (r ** 2) * (fx ** 2 + fy ** 2)).astype(np.float32)
        out = np.fft.irfft2(np.fft.rfft2(ap) * _kc[k2], s=ap.shape)
        return out[pad:pad + h, pad:pad + w].astype(np.float32)
    return np.fft.irfft2(np.fft.rfft2(a) * _kc[key], s=a.shape).astype(np.float32)

def chaikin(pts, it=3, closed=True):
    for _ in range(it):
        out = []
        n = len(pts)
        for i in range(n if closed else n - 1):
            p, q = np.array(pts[i]), np.array(pts[(i + 1) % n])
            out += [tuple(.75 * p + .25 * q), tuple(.25 * p + .75 * q)]
        pts = out
    return pts

def silhouette(view):
    nk = 236 if view == 'back' else 240
    P = []
    P += [(566, nk)]
    P += curve((566, nk), (450, 262), (332, 292), 20)            # shoulder
    P += curve((332, 292), (220, 400), (138, 566), 24)            # sleeve top
    P += curve((138, 566), (200, 640), (262, 690), 10)            # cuff
    P += curve((262, 690), (330, 640), (390, 586), 14)            # sleeve under
    P += curve((390, 586), (388, 1000), (398, 1404), 24)          # side
    P += curve((398, 1404), (700, 1420), (1002, 1404), 30)        # hem
    R = [(1400 - x, y) for x, y in P]
    pts = P[:-0 or None]
    left = P
    right = list(reversed([(1400 - x, y) for x, y in P]))
    pts = left[:-30] + [(x, y) for x, y in P[-30:]] + right[:-1]
    S = 2
    im = Image.new('L', (W * S, H * S), 0)
    ImageDraw.Draw(im).polygon([(x * S, y * S) for x, y in left + right], fill=255)
    m = np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.float32) / 255
    m = np.clip((blur(m, 2.5) - 0.5) * 2.2 + 0.5, 0, 1)
    return m

def line_layer(lines, S=1):
    im = Image.new('F', (W, H), 0)
    d = ImageDraw.Draw(im)
    for (x1, y1, x2, y2, w, v) in lines:
        d.line([(x1, y1), (x2, y2)], fill=v, width=w)
    return np.asarray(im, dtype=np.float32)

def poly_layer(polys):
    S = 2
    im = Image.new('L', (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([(x * S, y * S) for x, y in p], fill=255)
    return np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.float32) / 255

def curve(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.array, (p0, p1, p2))
    return [tuple(v) for v in ((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2)]

def stroke(pts, width):
    S = 2
    im = Image.new('L', (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    d.line([(x * S, y * S) for x, y in pts], fill=255, width=int(width * S), joint='curve')
    return np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.float32) / 255

def render(tee_rgb, prints, view='back', out='out.jpg', wash=0.5, seed=1):
    rng = np.random.default_rng(seed)
    m = silhouette(view)
    # ---------- height field ----------
    base = np.clip(blur(m, 26), 0, 1) ** 0.7
    folds = line_layer([
        (395, 590, 585, 800, 46, 1.0), (1005, 590, 815, 800, 46, 1.0),
        (410, 640, 520, 920, 30, -.7), (990, 640, 880, 920, 30, -.7),
        (200, 610, 345, 520, 34, .9), (1200, 610, 1055, 520, 34, .9),
        (240, 650, 360, 590, 20, -.6), (1160, 650, 1040, 590, 20, -.6),
        (470, 1404, 500, 1240, 40, .8), (930, 1404, 905, 1250, 40, .8),
        (620, 1410, 650, 1300, 26, -.5), (780, 1410, 760, 1290, 30, .6),
        (560, 260, 470, 380, 24, .5), (840, 260, 930, 380, 24, .5),
        (420, 1100, 440, 1350, 34, .5), (980, 1100, 960, 1350, 34, -.4),
    ])
    folds = blur(folds, 22)
    lowN = blur(rng.standard_normal((H, W)).astype(np.float32), 45)
    lowN /= np.abs(lowN).max() + 1e-6
    wr = blur(np.asarray(Image.fromarray(rng.standard_normal((H // 40, W // 14)).astype(np.float32), 'F').resize((W, H), Image.BICUBIC)), 14)
    h = base * 34 + folds * 24 + lowN * 10 + wr * 1.2
    gy, gx = np.gradient(h)
    nz = np.ones_like(h) * 1.0
    nx, ny = -gx, -gy
    nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    L = np.array([-0.45, -0.65, 0.95]); L /= np.linalg.norm(L)
    diff = (nx * L[0] + ny * L[1] + nz * L[2]) / nl
    ao = np.clip(blur(m, 18) * 1.25, 0, 1) ** 0.8
    shade = (0.30 + 0.80 * diff + 0.10 * np.clip(diff - 0.82, 0, 1) * 6) * (0.55 + 0.45 * ao)
    # broad light falloff top-left
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shade *= 1.05 - 0.12 * (yy / H) - 0.05 * np.abs(xx - W * .45) / W
    # ---------- fabric ----------
    fine = rng.standard_normal((H, W)).astype(np.float32)
    fine = blur(fine, 0.7) * 0.9
    knit = np.sin(xx * 2 * np.pi / 3.2) * 0.5 + np.sin((yy + np.sin(xx * .9) * 1.5) * 2 * np.pi / 4.0) * 0.25
    slub = np.asarray(Image.fromarray(rng.standard_normal((H // 3, W // 60)).astype(np.float32), 'F').resize((W, H), Image.BICUBIC))
    tex = 1 + 0.03 * fine + 0.01 * knit + 0.006 * slub
    mott = blur(rng.standard_normal((H, W)).astype(np.float32), 30)
    mott = mott / (np.abs(mott).max() + 1e-6)
    # seams
    seamsL = []
    if True:
        seamsL.append(stroke(curve((338, 296), (360, 440), (392, 566)), 3))
        seamsL.append(stroke(curve((1062, 296), (1040, 440), (1008, 566)), 3))
        seamsL.append(stroke(curve((404, 1366), (700, 1378), (996, 1366)), 2.2))
        seamsL.append(stroke(curve((174, 588), (230, 640), (308, 672)), 2.2))
        seamsL.append(stroke(curve((1226, 588), (1170, 640), (1092, 672)), 2.2))
    seams = sum(seamsL)
    seam_glow = blur(seams, 6)
    col = np.array(tee_rgb, np.float32) / 255
    # stonewash: lighter at seams/edges, mottled
    edge = np.clip(1 - blur(m, 10) * 1.0, 0, 1) * m
    lift = wash * (0.05 * mott + 0.18 * seam_glow + 0.25 * edge * 0)
    fabric = col[None, None, :] * (tex * shade)[..., None]
    fabric = fabric + lift[..., None] * (1 - col[None, None, :]) * 0.6
    fabric -= (seams * 0.10)[..., None]
    # collar
    if view == 'back':
        neck_top = curve((560, 236), (700, 268), (840, 236))
        band = stroke(neck_top, 30)
        band = band * m
        rib = 1 + 0.06 * np.sin(xx * 2 * np.pi / 5.0)
        fabric = fabric * (1 - band[..., None]) + (fabric * 0.9 * rib[..., None]) * band[..., None]
        fabric -= (stroke(curve((546, 252), (700, 286), (854, 252)), 2) * 0.08)[..., None]
    else:
        # inside back of neck visible
        inner = poly_layer([curve((566, 240), (700, 226), (834, 240)) + list(reversed(curve((566, 240), (700, 352), (834, 240))))])
        band = stroke(curve((570, 246), (700, 358), (830, 246)), 30)
        fabric = fabric * (1 - inner[..., None]) + (fabric * 0.55) * inner[..., None]
        rib = 1 + 0.06 * np.sin(xx * 2 * np.pi / 5.0)
        fabric = fabric * (1 - band[..., None]) + (fabric * 0.92 * rib[..., None]) * band[..., None]
    # ---------- prints ----------
    for p in prints:
        art = Image.open(p['file']).convert('RGBA')
        w = p['w']; hgt = int(art.height * w / art.width)
        art = art.resize((w, hgt), Image.LANCZOS)
        A = np.zeros((H, W), np.float32); C = np.zeros((H, W, 3), np.float32)
        x0, y0 = p['cx'] - w // 2, p['y']
        arr = np.asarray(art, np.float32) / 255
        A[y0:y0 + hgt, x0:x0 + w] = arr[..., 3]
        C[y0:y0 + hgt, x0:x0 + w] = arr[..., :3]
        # warp by height gradient
        k = 1.6
        sx = np.clip(xx + gx * k, 0, W - 1).astype(np.int32)
        sy = np.clip(yy + gy * k, 0, H - 1).astype(np.int32)
        A = A[sy, sx]; C = C[sy, sx]
        # distress
        n1 = blur(rng.standard_normal((H, W)).astype(np.float32), 2.2)
        n2 = blur(rng.standard_normal((H, W)).astype(np.float32), 5)
        n1 /= n1.std(); n2 /= n2.std()
        crack = ((n1 + 0.9 * n2) > p.get('distress', 2.35)).astype(np.float32)
        speck = (rng.random((H, W)) > 0.985).astype(np.float32)
        A = A * (1 - crack) * (1 - 0.6 * speck) * (0.86 + 0.08 * fine.clip(-1, 1)) * p.get('opacity', 0.92)
        A *= m
        ink = C * (shade * (0.92 + 0.08 * tex))[..., None]
        ink = ink * (1 - 0.06 * knit[..., None] * 0)
        fabric = fabric * (1 - A[..., None]) + ink * A[..., None]
    # ---------- composite on studio bg ----------
    bgtop, bgbot = np.array([236, 235, 232], np.float32) / 255, np.array([224, 222, 218], np.float32) / 255
    t = (yy / H)[..., None]
    bg = bgtop * (1 - t) + bgbot * t
    vig = 1 - 0.06 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)[..., None] * 4
    bg = bg * vig
    sh = blur(np.roll(m, 18, axis=0), 28) * 0.22
    bg = bg * (1 - sh[..., None])
    outimg = bg * (1 - m[..., None]) + np.clip(fabric, 0, 1) * m[..., None]
    grain = rng.standard_normal((H, W, 1)).astype(np.float32) * 0.008
    outimg = np.clip(outimg + grain, 0, 1)
    img = Image.fromarray((outimg * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # woven side tab on left side seam
    tx, ty = 382, 1250
    d.rectangle([tx, ty, tx + 22, ty + 54], fill=(26, 24, 22))
    d.rectangle([tx + 4, ty + 6, tx + 8, ty + 48], fill=(214, 204, 182))
    d.line([(tx + 22, ty), (tx + 22, ty + 54)], fill=(10, 10, 10), width=2)
    if view == 'front':
        # inner neck label
        d.rectangle([668, 246, 732, 274], fill=(30, 28, 26))
        d.text((678, 251), "BELO", fill=(224, 214, 190))
    img.save(out, quality=88)

if __name__ == '__main__':
    import sys
    jobs = {
      'm1_back':  ((41, 40, 42), [dict(file='p1.png', w=610, cx=700, y=350)], 'back', 1),
      'm1_front': ((41, 40, 42), [dict(file='f1.png', w=250, cx=860, y=430)], 'front', 2),
      'm2_back':  ((228, 220, 203), [dict(file='p2.png', w=580, cx=700, y=350)], 'back', 3),
      'm2_front': ((228, 220, 203), [dict(file='f2.png', w=230, cx=860, y=420)], 'front', 4),
      'm3_back':  ((78, 79, 51), [dict(file='p3.png', w=600, cx=700, y=400)], 'back', 5),
      'm4_back':  ((139, 59, 34), [dict(file='p4.png', w=600, cx=700, y=380)], 'back', 6),
      'm5_back':  ((59, 58, 57), [dict(file='p5.png', w=600, cx=700, y=360)], 'back', 7),
    }
    names = sys.argv[1:] or list(jobs)
    for n in names:
        c, p, v, sd = jobs[n]
        render(c, p, v, n + '.jpg', seed=sd)
        print(n)
