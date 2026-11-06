import numpy as np
from PIL import Image, ImageDraw, ImageFilter
IMG = '/tmp/claude-0/-home-user-murillofm/7cfe7f2d-f058-57c5-9690-7a67857fa913/images/'
_kc = {}
def blur(a, r):
    a = np.asarray(a, np.float32); h, w = a.shape
    pad = int(min(3 * r, min(h, w) // 2)); ap = np.pad(a, pad, mode='edge'); hp, wp = ap.shape
    k = (hp, wp, r)
    if k not in _kc:
        fy = np.fft.fftfreq(hp)[:, None]; fx = np.fft.rfftfreq(wp)[None, :]
        _kc[k] = np.exp(-2 * np.pi ** 2 * r ** 2 * (fx ** 2 + fy ** 2)).astype(np.float32)
    return np.fft.irfft2(np.fft.rfft2(ap) * _kc[k], s=ap.shape)[pad:pad + h, pad:pad + w].astype(np.float32)

# view: file, crop box, kind ('dark' shirt on light bg / 'light' shirt on dark bg), threshold
VIEWS = {
  'R_front': ('9.jpg', (28, 62, 372, 412), 'dark', 150),
  'R_back':  ('9.jpg', (364, 62, 708, 412), 'dark', 150),
  'W_back':  ('10.jpg', (186, 182, 892, 870), 'light', 70),
  'W_front': ('10.jpg', (186, 1072, 892, 1744), 'light', 70),
  'B_front': ('11.jpg', (70, 6, 666, 540), 'dark', 200),
  'B_back':  ('11.jpg', (70, 560, 666, 1062), 'dark', 200),
}
TH = 1100  # working height

def load_view(name):
    f, box, kind, th = VIEWS[name]
    im = Image.open(IMG + f).convert('RGB').crop(box)
    sc = TH / im.height
    im = im.resize((round(im.width * sc), TH), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    L = a @ np.array([.299, .587, .114], np.float32)
    m = (L < th / 255) if kind == 'dark' else (L > th / 255)
    # background = candidate pixels connected to the border (iterative dilation)
    cand = ~m
    reach = np.zeros_like(cand); reach[0, :] = cand[0, :]; reach[-1, :] = cand[-1, :]; reach[:, 0] = cand[:, 0]; reach[:, -1] = cand[:, -1]
    prev = -1
    while True:
        for _ in range(25):
            r = reach.copy()
            r[1:] |= reach[:-1]; r[:-1] |= reach[1:]; r[:, 1:] |= reach[:, :-1]; r[:, :-1] |= reach[:, 1:]
            reach = r & cand
        s_ = int(reach.sum())
        if s_ == prev: break
        prev = s_
    bg = reach
    mask = (~bg).astype(np.float32)
    # erode 2px to drop fringe, soften
    er = {'R_front': (4.0, 0.88), 'R_back': (4.0, 0.88)}.get(name, (2.6, 0.82) if kind == 'light' else (1.5, 0.6))
    mask = np.clip((blur(mask, er[0]) - er[1]) / (1 - er[1]) * 1.6, 0, 1)
    mask = blur(mask, 0.8)
    return a, L, mask, kind

def unblend(art, paper, inks):
    """remove paper-colored knockouts from rendered art -> transparent"""
    arr = np.asarray(art, np.float32) / 255
    C, A = arr[..., :3], arr[..., 3]
    p = np.array(paper, np.float32) / 255
    d = np.linalg.norm(C - p, axis=-1)
    dmin = min(np.linalg.norm(np.array(i, np.float32) / 255 - p) for i in inks)
    t = np.clip(d / dmin, 0, 1)
    Cn = p + (C - p) / np.maximum(t, 1e-3)[..., None]
    return np.clip(Cn, 0, 1), A * t

def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def compose_view(name, color=None, prints=(), seed=1):
    rng = np.random.default_rng(seed)
    a, L, mask, kind = load_view(name)
    H, W = L.shape
    ys, xs = np.where(mask > .5); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    bw, bh, cx = x1 - x0, y1 - y0, (x0 + x1) / 2
    lift = bool(color) and kind == 'dark'          # dark photo recolored to another color
    r_ = 10.0 if lift else 1.2
    mm = (mask > .5).astype(np.float32)
    Ls = blur(L * mm, r_) / np.maximum(blur(mm, r_), 1e-3)
    med = np.median(Ls[mask > .5])
    S = Ls / max(med, 1e-3)
    comp = 0.30 if lift else (0.55 if kind == 'dark' else 1.0)
    Sc = np.clip(1 + comp * (S - 1), 0.72 if lift else 0.35, 1.18 if lift else 1.35)
    if lift:
        Sc = Sc * (1 - 0.10 * (1 - np.clip(blur(mask, 14) * 1.3, 0, 1)))   # soft edge falloff
    fine = blur(rng.standard_normal((H, W)).astype(np.float32), 0.7)
    knit = np.sin(np.arange(W)[None, :] * 2 * np.pi / 3.4) * 0.5
    if color:
        col = np.array(hexrgb(color), np.float32) / 255
        shirt = col[None, None, :] * Sc[..., None]
    else:
        shirt = a.copy()
    shirt = shirt * (1 + 0.035 * fine + 0.01 * knit)[..., None]
    # displacement from shading
    hs = blur(L, 5) - blur(L, 30)
    gy, gx = np.gradient(blur(hs, 2))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for p in prints:
        art = Image.open(p['file']).convert('RGBA')
        w = int(p['w'] * bw); hgt = int(art.height * w / art.width)
        art = art.resize((w, hgt), Image.LANCZOS)
        if p.get('paper'):
            C, A0 = unblend(art, hexrgb(p['paper']), [hexrgb(i) for i in p['inks']])
        else:
            arr = np.asarray(art, np.float32) / 255; C, A0 = arr[..., :3], arr[..., 3]
        A = np.zeros((H, W), np.float32); CC = np.zeros((H, W, 3), np.float32)
        px0 = int(cx + p.get('dx', 0) * bw - w / 2); py0 = int(y0 + p['top'] * bh)
        A[py0:py0 + hgt, px0:px0 + w] = A0; CC[py0:py0 + hgt, px0:px0 + w] = C
        k = 260 if kind == 'light' else 520
        sx = np.clip(xx + gx * k, 0, W - 1).astype(np.int32); sy = np.clip(yy + gy * k, 0, H - 1).astype(np.int32)
        A = A[sy, sx]; CC = CC[sy, sx]
        n1 = blur(rng.standard_normal((H, W)).astype(np.float32), 1.8); n2 = blur(rng.standard_normal((H, W)).astype(np.float32), 4.5)
        n1 /= n1.std(); n2 /= n2.std()
        crack = ((n1 + 0.9 * n2) > 2.35).astype(np.float32)
        speck = (rng.random((H, W)) > 0.986).astype(np.float32)
        light_tee = float(np.median(shirt[mask > .5].mean(-1))) > 0.5
        A = A * (1 - crack) * (1 - 0.6 * speck) * ((0.97 + 0.03 * np.clip(fine, -1, 1)) if light_tee else (0.86 + 0.08 * np.clip(fine, -1, 1))) * (1.0 if light_tee else 0.94) * mask
        inkS = np.clip(1 + (0.6 if kind == 'light' else 0.35) * (S - 1), 0.55, 1.15)
        ink = CC * inkS[..., None]
        shirt = shirt * (1 - A[..., None]) + ink * A[..., None]
    return np.clip(shirt, 0, 1), mask

def studio(views, out, gap=60, pad=90):
    """views: list of (rgb, mask). Lay out side by side on a studio background."""
    H = max(v[0].shape[0] for v in views) + 2 * pad
    Wt = sum(v[0].shape[1] for v in views) + gap * (len(views) - 1) + 2 * pad
    yy, xx = np.mgrid[0:H, 0:Wt].astype(np.float32)
    top, bot = np.array([236, 235, 232], np.float32) / 255, np.array([222, 220, 216], np.float32) / 255
    bg = top * (1 - yy / H)[..., None] + bot * (yy / H)[..., None]
    bg *= (1 - 0.05 * (((xx - Wt / 2) / Wt) ** 2 + ((yy - H / 2) / H) ** 2) * 4)[..., None]
    x = pad
    for rgb, m in views:
        h, w = m.shape; y = (H - h) // 2
        M = np.zeros((H, Wt), np.float32); M[y:y + h, x:x + w] = m
        R = np.zeros((H, Wt, 3), np.float32); R[y:y + h, x:x + w] = rgb
        sh = blur(np.roll(M, 16, axis=0), 24) * 0.22
        bg = bg * (1 - sh[..., None])
        bg = bg * (1 - M[..., None]) + R * M[..., None]
        x += w + gap
    g = np.random.default_rng(3).standard_normal((H, Wt, 1)).astype(np.float32) * 0.007
    Image.fromarray((np.clip(bg + g, 0, 1) * 255).astype(np.uint8)).save(out, quality=88)
