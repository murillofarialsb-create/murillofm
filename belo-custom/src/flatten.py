import sys, re, subprocess, xml.etree.ElementTree as ET
import numpy as np
from svgelements import SVG, Path, Shape, Group, Matrix, ClipPath, Close, Move
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import make_valid
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS); ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
PROPS = ['fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'fill-rule', 'stroke-dasharray']

def parse_style(s):
    d = {}
    for part in (s or '').split(';'):
        if ':' in part:
            k, v = part.split(':', 1); d[k.strip()] = v.strip()
    return d

def propagate(src, dst):
    tree = ET.parse(src); root = tree.getroot()
    def walk(el, inh):
        st = parse_style(el.get('style'))
        mine = dict(inh)
        for p in PROPS:
            if p in st: mine[p] = st[p]
            elif el.get(p) is not None: mine[p] = el.get(p)
        tag = el.tag.split('}')[-1]
        if tag in ('path', 'rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline'):
            for p, v in mine.items():
                if p not in st: el.set(p, v)
        if tag in ('clipPath', 'defs'):
            return
        for c in el: walk(c, {k: v for k, v in mine.items() if k != 'opacity'} if tag != 'g' else mine)
    walk(root, {})
    tree.write(dst)

def to_geom(shape, tol=0.35):
    p = Path(shape) if not isinstance(shape, Path) else shape
    rings, cur = [], []
    for seg in p:
        if isinstance(seg, Move):
            if len(cur) > 2: rings.append(cur)
            cur = [(seg.end.x, seg.end.y)]
            continue
        if isinstance(seg, Close):
            if len(cur) > 2: rings.append(cur)
            cur = []
            continue
        try:
            L = seg.length(error=1e-2)
        except Exception:
            L = 10
        n = max(1, int(L / tol)) if type(seg).__name__ != 'Line' else 1
        for t in np.linspace(0, 1, n + 1)[1:]:
            q = seg.point(t); cur.append((q.x, q.y))
    if len(cur) > 2: rings.append(cur)
    g = None
    for r in rings:
        poly = make_valid(Polygon(r))
        g = poly if g is None else g.symmetric_difference(poly)
    return g

def hexn(c):
    return str(c).lower() if c is not None else None

def flatten(src_outlined, paper, out_svg, label_inks):
    T = out_svg + '.'
    propagate(src_outlined, T + 'prop.svg')
    subprocess.run(['inkscape', T + 'prop.svg', f'--actions=select-all:all;object-to-path;object-stroke-to-path;export-filename:{T}s.svg;export-plain-svg;export-do'], capture_output=True)
    # tag descendants of clipped groups so svgelements keeps the reference
    tree = ET.parse(T + 's.svg'); root = tree.getroot()
    clipsrc = {}
    for el in root.iter():
        if el.tag.split('}')[-1] == 'clipPath':
            ds = []
            for c in el.iter():
                t = c.tag.split('}')[-1]
                f = lambda k, d=0: float(c.get(k, d))
                if c.get('d'): ds.append(c.get('d'))
                elif t == 'rect': ds.append(f"M{f('x')},{f('y')} h{f('width')} v{f('height')} h{-f('width')} Z")
                elif t in ('circle', 'ellipse'):
                    cx, cy = f('cx'), f('cy'); rx = f('r') if t == 'circle' else f('rx'); ry = f('r') if t == 'circle' else f('ry')
                    ds.append(f"M{cx-rx},{cy} A{rx},{ry} 0 1 0 {cx+rx},{cy} A{rx},{ry} 0 1 0 {cx-rx},{cy} Z")
            clipsrc[el.get('id')] = ds
    def tag(el, cid, ctf, chain):
        chain = chain + ([el.get('transform')] if el.get('transform') else [])
        c = el.get('clip-path')
        if c:
            m = re.search(r'#([^)]+)', c)
            if m: cid, ctf = m.group(1), ' '.join(chain)
        if cid and el.tag.split('}')[-1] in ('path', 'rect', 'circle', 'ellipse', 'line', 'polygon', 'polyline'):
            el.set('data-clip', cid); el.set('data-cliptf', ctf)
        if el.tag.split('}')[-1] == 'clipPath': return
        for ch in el: tag(ch, cid, ctf, chain)
    tag(root, None, '', [])
    tree.write(T + 't.svg')
    svg = SVG.parse(T + 't.svg', reify=False)
    clipcache = {}
    layers = {}   # color -> geometry
    order = []
    for el in svg.elements():
        if not isinstance(el, Shape): continue
        # skip shapes that live inside clipPath definitions
        anc = el
        inside_clip = False
        # svgelements keeps clipPath children out of elements() normally; guard anyway
        if el.values.get('opacity') not in (None, '1', 1, 1.0):
            try:
                if float(el.values.get('opacity')) == 0: continue
            except Exception: pass
        fill = el.fill
        if fill is None or fill.value is None: continue
        col = hexn(fill.hex)[:7]
        g = to_geom(abs(Path(el)))
        if g is None or g.is_empty: continue
        cid = el.values.get('data-clip')
        if cid and cid in clipsrc:
            ctf = el.values.get('data-cliptf') or ''
            key = (cid, ctf)
            if key not in clipcache:
                cg = None
                M = Matrix(ctf) if ctf else Matrix()
                for d in clipsrc[cid]:
                    pp = abs(Path(d) * M)
                    gg = to_geom(pp)
                    if gg is not None: cg = gg if cg is None else cg.union(gg)
                clipcache[key] = cg
            if clipcache[key] is not None:
                g = g.intersection(clipcache[key])
        if g.is_empty: continue
        for k in list(layers):
            if k != col: layers[k] = layers[k].difference(g)
        layers[col] = layers[col].union(g) if col in layers else g
        if col not in order: order.append(col)
    paper = paper.lower()
    vb = svg.viewbox
    w, h = svg.width, svg.height
    parts = [f'<svg xmlns="{NS}" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    n = 0
    for col in order:
        if col == paper: continue
        geom = layers[col]
        if geom.is_empty: continue
        n += 1
        d = geom_to_d(geom)
        name = label_inks.get(col, col.upper())
        parts.append(f'<g id="tinta-{n}" inkscape:groupmode="layer" inkscape:label="Tinta {n} · {name}"><path fill="{col.upper()}" fill-rule="evenodd" d="{d}"/></g>')
    parts.append('</svg>')
    open(out_svg, 'w').write('\n'.join(parts))
    return [c for c in order if c != paper and not layers[c].is_empty]

def geom_to_d(geom):
    polys = [geom] if geom.geom_type == 'Polygon' else [g for g in getattr(geom, 'geoms', []) if g.geom_type == 'Polygon']
    if geom.geom_type == 'GeometryCollection':
        polys = [g for g in geom.geoms if g.geom_type == 'Polygon'] + [p for g in geom.geoms if g.geom_type == 'MultiPolygon' for p in g.geoms]
    out = []
    for p in polys:
        p = p.simplify(0.05)
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            if len(cs) < 3: continue
            out.append('M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in cs[:-1]) + 'Z')
    return ' '.join(out)

if __name__ == '__main__':
    src, paper, out = sys.argv[1], sys.argv[2], sys.argv[3]
    NAMES = {'#e07650': 'Terra claro', '#26389a': 'Azul cobalto', '#e4dcc9': 'Osso', '#e9e0cc': 'Osso', '#e0a526': 'Ipê', '#1e1b18': 'Graxa', '#b8481f': 'Terra', '#c9572c': 'Terra claro'}
    print(out, flatten(src, paper, out, NAMES))
