// Optional developer-only visual QA; not a dependency of the translation toolkit.
const fs = require('node:fs');
const path = require('node:path');
const { marked } = require('marked');
const { chromium } = require('playwright');
(async () => {
  const root = path.resolve(__dirname, '../..');
  const out = path.join(root, 'translation-work/.state/preview');
  fs.mkdirSync(out, { recursive: true });
  const body = marked.parse(fs.readFileSync(path.join(root, 'README.md'), 'utf8'));
  const html = `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
  *{box-sizing:border-box}body{font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1f2328;background:#fff;margin:0;padding:24px}.markdown-body{max-width:960px;margin:auto}img{max-width:100%;height:auto}a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}h1,h2{border-bottom:1px solid #d1d9e0;padding-bottom:.3em;line-height:1.25}h2{margin-top:28px}pre{background:#f6f8fa;padding:16px;border-radius:6px;overflow:auto}code{font-size:.9em;background:#f6f8fa}li{margin:.3em 0}hr{border:0;border-top:1px solid #d1d9e0;margin:28px 0}summary{cursor:pointer}details{margin:18px 0}p{margin:14px 0}@media(max-width:500px){body{padding:16px}h1{font-size:1.75rem}h2{font-size:1.35rem}}
  </style><article class="markdown-body">${body}</article></html>`;
  fs.writeFileSync(path.join(out, 'README.html'), html);
  let browser;
  try { browser = await chromium.launch({headless:true}); }
  catch { browser = await chromium.launch({headless:true,channel:'msedge'}); }
  try {
    const page = await browser.newPage();
    await page.setContent(html, {waitUntil:'networkidle'});
    const images = await page.locator('img').evaluateAll(xs => xs.map(x=>({src:x.src,ok:x.complete&&x.naturalWidth>0})));
    for(const width of [1100,390]){
      await page.setViewportSize({width,height:900});
      await page.screenshot({path:path.join(out,`README-${width}.png`),fullPage:true});
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
      console.log(JSON.stringify({width,overflow,images}));
      if(overflow)process.exitCode=1;
    }
  } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
