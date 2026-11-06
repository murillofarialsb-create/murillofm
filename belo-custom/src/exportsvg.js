const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.cwd() + '/prints.html', { waitUntil: 'networkidle' });
  const ids = ['p1','p2','p3','p4','p5','f1','f2','n1','n2','n3','o1','o2','o3','ch1','ch2'];
  for (const id of ids) {
    const s = await p.evaluate(id => { const e = document.getElementById(id).cloneNode(true); e.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink'); e.querySelectorAll('textPath').forEach(t => t.setAttribute('xlink:href', t.getAttribute('href'))); return new XMLSerializer().serializeToString(e); }, id);
    fs.writeFileSync(`vec/raw/${id}.svg`, '<?xml version="1.0" encoding="UTF-8"?>\n' + s);
  }
  await b.close();
})();
