const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ deviceScaleFactor: 1.6 });
  await p.goto('file://' + process.cwd() + '/prints.html', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(800);
  for (const id of ['p1','p2','p3','p4','p5','f1','f2']) {
    await p.locator('#' + id).screenshot({ path: id + '.png', omitBackground: true });
  }
  await b.close();
})();
