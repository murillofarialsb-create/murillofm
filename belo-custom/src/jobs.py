import sys
exec(open('photo.py').read())
OS, GX, IPE, TERRA = '#E9E0CC', '#1E1B18', '#E0A526', '#B8481F'
def chest(c): return dict(file='ch1.png' if c == 'light' else 'ch2.png', w=.15, dx=.17, top=.23)
J = [
 ('01-house-of-slow-machines', 'B', None, [dict(file='f1.png', w=.17, dx=.17, top=.22, paper='#29282A', inks=['#E07650'])], [dict(file='p1.png', w=.45, top=.16, paper='#29282A', inks=['#E07650'])]),
 ('02-ipe-engine', 'W', '#E4DCC9', [dict(file='f2.png', w=.15, dx=.17, top=.21, paper='#E4DCC9', inks=['#26389A'])], [dict(file='p2.png', w=.43, top=.15, paper='#E4DCC9', inks=['#26389A'])]),
 ('03-slow-is-a-speed', 'W', '#4E4F33', [chest('light')], [dict(file='p3.png', w=.44, top=.17, paper='#4E4F33', inks=['#E4DCC9', IPE])]),
 ('04-moto-works', 'W', '#8B3B22', [chest('light')], [dict(file='p4.png', w=.45, top=.16, paper='#8B3B22', inks=['#E9E0CC', IPE])]),
 ('05-long-way-home', 'B', None, [chest('light')], [dict(file='p5.png', w=.45, top=.16, paper='#3B3A39', inks=['#E9E0CC', IPE])]),
 ('06-belo-ignition-co', 'R', '#E4DCC9', [chest('dark')], [dict(file='n1.png', w=.40, top=.15, paper='#E4DCC9', inks=[GX, TERRA])]),
 ('07-two-speeds', 'R', None, [chest('light')], [dict(file='n2.png', w=.40, top=.16, paper='#29282A', inks=[OS, IPE])]),
 ('08-open-face-society', 'R', '#A9A6A0', [dict(file='n3.png', w=.34, dx=0, top=.17, paper='#A9A6A0', inks=[GX, TERRA])], []),
 ('09-anatomia-de-um-v2', 'W', '#E4DCC9', [chest('dark')], [dict(file='o1.png', w=.44, top=.14, paper='#E4DCC9', inks=[GX])]),
 ('10-garage-goods-union', 'B', None, [chest('light')], [dict(file='o2.png', w=.45, top=.16, paper='#29282A', inks=[OS, '#C9572C'])]),
 ('11-belo-motor-oil', 'W', '#2C3448', [chest('light')], [dict(file='o3.png', w=.45, top=.16, paper='#2C3448', inks=[OS, IPE])]),
]
only = sys.argv[1:]
for i, (name, t, col, fr, bk) in enumerate(J):
    if only and not any(o in name for o in only): continue
    f = compose_view(t + '_front', col, fr, seed=i * 2 + 1)
    b = compose_view(t + '_back', col, bk, seed=i * 2 + 2)
    studio([f, b], f'out_{name}.jpg')
    print(name)
