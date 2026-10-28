/* Isolated headless browser verification; never connects to a user's browser. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const arg = (name) => args.includes(name) ? args[args.indexOf(name)+1] : '';
const output = arg('--output');
const site = path.join(root,'site/light');
const read = (file) => JSON.parse(fs.readFileSync(path.join(site,file),'utf8'));
const manifest = read('manifest.json');
let server, browser;
(async () => {
  let base = arg('--url');
  if (!base) {
    server = http.createServer((req,res) => {
      const requestPath = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      if (!requestPath.startsWith('/tw-public-library-statistics/')) {res.writeHead(404).end();return;}
      const relative = requestPath.slice('/tw-public-library-statistics/'.length) || 'index.html';
      const target = path.resolve(site,relative);
      if (!target.startsWith(site+path.sep) || !fs.existsSync(target) || !fs.statSync(target).isFile()) {res.writeHead(404).end();return;}
      res.setHeader('Content-Type', ({'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8'})[path.extname(target)] || 'application/octet-stream');
      res.end(fs.readFileSync(target));
    });
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    base = `http://127.0.0.1:${server.address().port}/tw-public-library-statistics/`;
  }
  browser = await chromium.launch({headless:true});
  const results = [];
  for (const width of [320,390,768,1440]) {
    const context = await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1});
    const page = await context.newPage();const errors=[],requests=[];
    page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>requests.push(r.url()));
    await page.goto(base,{waitUntil:'networkidle'});
    await page.locator('#result').waitFor({state:'visible'});
    const actual = await page.evaluate(() => ({
      width:innerWidth,documentWidth:document.documentElement.scrollWidth,
      ticks:[...document.querySelectorAll('.y-tick,.x-tick')].filter(n=>n.getClientRects().length).map(n=>Number.parseFloat(getComputedStyle(n).fontSize)),
      points:[...document.querySelectorAll('.plot-point')].map(n=>({key:n.dataset.recordKey,url:n.href,label:n.getAttribute('aria-label')})),
      values:[...document.querySelectorAll('.value-link')].map(n=>({key:n.closest('tr').dataset.recordKey,url:n.href,text:n.textContent})),
      selected:document.getElementById('series').value
    }));
    assert.equal(actual.documentWidth,width,'Whole-page mobile overflow');assert(actual.ticks.length && actual.ticks.every(n=>n>=12),'Axis labels too small');
    const catalog=read(manifest.profiles.find(p=>p.id===manifest.default_profile_id).catalog_url);
    const series=read(catalog.series.find(s=>s.id===actual.selected).url);const keys=new Set(catalog.default_selection.selected_record_keys);
    const records=series.records.filter(r=>keys.has(r.record_key));
    assert.deepEqual(actual.values,records.map(r=>({key:r.record_key,url:new URL(r.official_url).href,text:r.display_value})));
    assert.equal(actual.points.length,records.filter(r=>r.plot).length);assert(actual.points.every(p=>p.url===new URL(records.find(r=>r.record_key===p.key).official_url).href));
    const jsonRequests=requests.filter(u=>new URL(u).pathname.endsWith('.json'));
    assert.equal(jsonRequests.length,3,'Initial load must fetch only manifest, chosen catalog and one series');
    const entries=await page.evaluate(()=>performance.getEntriesByType('resource').map(r=>({name:r.name,bytes:r.decodedBodySize})));
    const initialBytes=entries.reduce((n,r)=>n+r.bytes,0)+(await page.content()).length;
    assert(initialBytes<1024*1024,'Actual initial load exceeded 1 MiB');assert.deepEqual(errors,[]);
    if (output) {fs.mkdirSync(output,{recursive:true});await page.screenshot({path:path.join(output,`default-${width}.png`),fullPage:true});}
    results.push({width,document_width:actual.documentWidth,min_tick_font_px:Math.min(...actual.ticks),initial_json_requests:jsonRequests.length,decoded_resource_bytes:entries.reduce((n,r)=>n+r.bytes,0),plotted_points:actual.points.length,source_links_checked:actual.values.length});
    await context.close();
  }
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();const requests=[];
  page.on('request',r=>requests.push(r.url()));
  await page.goto(base+'?profile=national-ncl-count-panel&from=2018&to=2024',{waitUntil:'networkidle'});
  await page.locator('#status.is-empty').waitFor();
  assert.equal(await page.locator('.plot-point').count(),0,'Unresolved interval retained old chart');assert.equal(await page.locator('#records-body tr').count(),0);
  await page.goto(base+'?profile=national-ncl-book-loans-panel&from=2020&to=2024',{waitUntil:'networkidle'});
  await page.locator('#result').waitFor({state:'visible'});assert.equal(await page.locator('.plot-point').count(),5);assert.equal(await page.locator('.data-line').count(),4);
  const loaded=requests.length;await page.selectOption('#from','2021');await page.waitForTimeout(150);
  assert.equal(await page.locator('.plot-point').count(),4);assert.equal(requests.length,loaded,'Same chart should reuse its cache');
  await page.selectOption('#from','');await page.locator('#status.is-empty').waitFor();assert.equal(await page.locator('.plot-point').count(),0,'Incomplete period retained chart');
  const raw=read(manifest.original_catalog_url);const monthly=raw.series.find(s=>s.entity==='新竹市' && s.years.length>5);
  await page.goto(base+'?mode=original&series='+encodeURIComponent(monthly.id),{waitUntil:'networkidle'});
  await page.locator('#result').waitFor({state:'visible'});const monthlyData=read(monthly.url);
  assert.equal(await page.locator('.plot-point').count(),monthlyData.records.filter(r=>r.plot).length);assert.equal(await page.locator('.data-line').count(),monthlyData.lines.length,'Monthly gaps were bridged');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390,'Long source details overflow mobile');
  await page.goto(base+'?profile=county-library-count-dgbas&entity='+encodeURIComponent('臺南市'),{waitUntil:'networkidle'});
  await page.locator('#result').waitFor({state:'visible'});assert(await page.locator('#official-link-note').isVisible(),'Dynamic official query needs a visible reproduction note');
  await page.route('**/data/*.json',r=>r.abort());
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#status.is-error').waitFor();assert.equal(await page.locator('.plot-point').count(),0,'Failed load retained old data');assert(await page.locator('#retry').isVisible());
  await context.close();
  console.log(JSON.stringify({passed:true,mobile_and_desktop:results,checked_cases:['exact 2020–2024 interval','unresolved interval clears chart','incomplete period clears chart','series cache','monthly original gaps','dynamic official entry note','network failure with retry'],isolated_headless:true}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));});
