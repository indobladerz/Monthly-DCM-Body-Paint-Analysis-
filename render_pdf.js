// Render out/report.html to out/report.pdf (A4) and page images for visual QA.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1180, height: 900 } });
  await page.goto('file://' + path.resolve('out/report.html'), { waitUntil: 'load' });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: 'out/report.pdf', format: 'A4', printBackground: true, margin: { top: '12mm', bottom: '12mm', left: '10mm', right: '10mm' } });
  await page.emulateMedia({ media: 'screen' });
  await page.screenshot({ path: 'out/preview.png', fullPage: true });
  await browser.close();
  console.log('pdf + preview written');
})();
