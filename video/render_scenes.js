const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const url = 'file://' + path.resolve(__dirname, 'scenes.html');
  const list = process.argv.slice(2).length ? process.argv.slice(2) :
    ['p1s1','p1s2','p1s3','p1s4','p1s5','p1s6','p2s1','p2s2','p2s3','p2s4','p2s5','p2s6'];
  for (const s of list) {
    await p.goto(url + '?scene=' + s);
    await p.screenshot({ path: path.join(__dirname, 'build', s + '.png') });
  }
  await b.close();
})();
