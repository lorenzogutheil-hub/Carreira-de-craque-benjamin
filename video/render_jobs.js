// usage: node render_jobs.js jobs.json   -> [{q:"type=caption&text=..", out:"path.png", transparent:true}]
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const url = 'file://' + path.resolve(__dirname, 'scenes.html');
  for (const j of jobs) {
    await p.goto(url + '?' + j.q);
    await p.screenshot({ path: j.out, omitBackground: !!j.transparent });
  }
  await b.close();
})();
