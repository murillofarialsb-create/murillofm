const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
  await p.goto('file://' + process.cwd() + '/ig/posts.html', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(600);
  for (let i = 1; i <= 9; i++) await p.locator('#p' + i).screenshot({ path: `ig/post${i}.jpg`, type: 'jpeg', quality: 90 });
  await b.close();
})();
