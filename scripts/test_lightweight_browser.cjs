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
const site = path.resolve(arg('--site') || path.join(root,'site/light'));
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
  browser = await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? {executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH} : {})});
  const results = [];
  for (const width of [320,375,390,768,1440]) {
    const context = await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1});
    const page = await context.newPage();const errors=[],requests=[];
    page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>requests.push(r.url()));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
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
    assert(!requests.some(u=>u.endsWith(manifest.source_batches[0].catalog_url)),'Default load eagerly fetched source batch');
    assert.match(await page.locator('#human-review-status').innerText(),/人工核讀 0\/120；人工雙校未完成/);
    const entries=await page.evaluate(()=>performance.getEntriesByType('resource').map(r=>({name:r.name,bytes:r.decodedBodySize})));
    const initialBytes=entries.reduce((n,r)=>n+r.bytes,0)+(await page.content()).length;
    assert(initialBytes<1024*1024,'Actual initial load exceeded 1 MiB');assert.deepEqual(errors,[]);
    if (output) {fs.mkdirSync(output,{recursive:true});await page.screenshot({path:path.join(output,`default-${width}.png`),fullPage:true});}
    results.push({width,document_width:actual.documentWidth,min_tick_font_px:Math.min(...actual.ticks),initial_json_requests:jsonRequests.length,decoded_resource_bytes:entries.reduce((n,r)=>n+r.bytes,0),plotted_points:actual.points.length,source_links_checked:actual.values.length});
    await context.close();
  }
  const batchEntry=manifest.source_batches.find(b=>b.id==='ncl94-statistics');
  const batch=read(batchEntry.catalog_url);const batchResults=[];
  for(const width of [320,375,1440]) {
    const batchContext=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1});
    const batchPage=await batchContext.newPage();const errors=[],requests=[];
    batchPage.on('pageerror',e=>errors.push(String(e)));batchPage.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    batchPage.on('request',r=>requests.push(r.url()));
    await batchPage.goto(base+'?batch=ncl94-statistics',{waitUntil:'domcontentloaded'});
    await batchPage.locator('#source-batch').waitFor({state:'visible'});
    const actual=await batchPage.locator('#batch-records tr').evaluateAll(rows=>rows.map(r=>({
      id:r.dataset.observationId,physical:r.dataset.physicalCellId,role:r.dataset.quantityRole,
      value:r.querySelector('.batch-value-link').textContent,url:r.querySelector('.batch-value-link').href,
      text:r.textContent,fullCell:r.querySelector('.physical-cell-link').textContent,fullCellURL:r.querySelector('.physical-cell-link').href
    })));
    assert.deepEqual(actual.map(r=>({id:r.id,physical:r.physical,role:r.role,value:r.value,url:r.url,fullCell:r.fullCell,fullCellURL:r.fullCellURL})),batch.records.map(r=>({id:r.observation_id,physical:r.physical_cell_id,role:r.quantity_role,value:r.raw_value,url:new URL(r.source_url).href,fullCell:r.physical_cell_raw,fullCellURL:new URL(r.source_url).href})));
    for(const record of batch.records) {
      const row=actual.find(r=>r.id===record.observation_id);
      for(const token of [record.source_sha256,record.source_version_id,record.source_locator,record.population_scope,`列${record.source_row}／欄${record.source_column}`])assert(row.text.includes(token),'Missing source detail: '+token);
      assert(row.text.includes('精確起訖未確認'));
      if(record.unit===null)assert(row.text.includes('null（未知；原刊未獨立印出）'));
      if(record.quantity_role==='responding_libraries')assert(row.text.includes('括號填答館數；非館總數'));
    }
    assert.equal(await batchPage.locator('.data-line,.plot-point').count(),0,'Single-period batch gained plotted lines/points');
    assert(await batchPage.locator('#result').isHidden());
    assert.equal(await batchPage.locator('#mode').inputValue(),'batch');
    assert.match(await batchPage.locator('#batch-review-status').innerText(),/人工核讀 0\/120；人工雙校未完成/);
    assert.equal(requests.filter(u=>new URL(u).pathname.endsWith('.json')).length,2,'Batch deep link must fetch only manifest and chosen batch');
    assert.equal(await batchPage.evaluate(()=>document.documentElement.scrollWidth),width,'Source batch page horizontal overflow');
    const table=await batchPage.locator('#batch-table').evaluate(n=>({table:n.scrollWidth,region:n.parentElement.clientWidth,font:parseFloat(getComputedStyle(n).fontSize)}));
    assert(table.font>=14,'Source table font too small');if(width<1180)assert(table.table>table.region,'Mobile table should have its own horizontal scroll');
    await batchPage.locator('#batch-records details').first().evaluate(n=>n.open=true);
    assert(await batchPage.locator('#batch-records details').first().locator('dl').isVisible());
    assert.equal(await batchPage.evaluate(()=>document.documentElement.scrollWidth),width,'Expanded source detail horizontal overflow');
    await batchPage.reload({waitUntil:'domcontentloaded'});await batchPage.locator('#source-batch').waitFor({state:'visible'});
    assert.equal(await batchPage.locator('#batch-records tr').count(),24,'Reload lost deep-linked batch');
    assert.deepEqual(errors,[]);
    if(output) {
      await batchPage.screenshot({path:path.join(output,`ncl94-batch-${width}.png`),fullPage:true});
      await batchPage.screenshot({path:path.join(output,`ncl94-batch-${width}-viewport.png`),fullPage:false});
      await batchPage.locator('#batch-table').scrollIntoViewIfNeeded();
      await batchPage.screenshot({path:path.join(output,`ncl94-batch-${width}-table-viewport.png`),fullPage:false});
    }
    batchResults.push({width,records:actual.length,physical_cells:new Set(actual.map(r=>r.physical)).size,new_lines:0,cold_json_requests:2,document_width:width,table_font_px:table.font,console_errors:errors});
    await batchContext.close();
  }
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();const requests=[],interactionErrors=[];
  page.on('pageerror',e=>interactionErrors.push(String(e)));page.on('console',m=>{if(m.type()==='error')interactionErrors.push(m.text());});
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
  const newProfileChecks=[];
  for (const profileId of ['discovered-official-annual-tables','discovered-official-monthly-tables']) {
    const profile=manifest.profiles.find(p=>p.id===profileId);if(!profile)continue;
    const catalog=read(profile.catalog_url);
    const series=profileId.endsWith('annual-tables')
      ? catalog.series.find(s=>s.entity==='新北市' && s.indicator==='借閱人次')
      : catalog.series.find(s=>s.entity==='三民分館' && s.source_id.includes('kaohsiung') && s.indicator.includes('借閱冊') && !s.indicator.includes('率'));
    assert(series,'Complete new source series missing from public profile');
    await page.goto(base+'?profile='+profileId+'&series='+encodeURIComponent(series.id),{waitUntil:'networkidle'});
    await page.locator('#result').waitFor({state:'visible'});
    const content=read(series.url),selected=new Set(catalog.default_selection.selected_record_keys);
    const records=content.records.filter(r=>selected.has(r.record_key));
    const actual=await page.locator('.value-link').evaluateAll(nodes=>nodes.map(n=>({url:n.href,text:n.textContent,key:n.closest('tr').dataset.recordKey})));
    assert.deepEqual(actual,records.map(r=>({url:new URL(r.official_url).href,text:r.display_value,key:r.record_key})));
    assert.equal(await page.locator('.plot-point').count(),records.filter(r=>r.plot).length);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390,'New source table overflows mobile');
    if(profileId.endsWith('annual-tables')) {
      assert(records.some(r=>r.year===2006 && r.raw_value==='…' && r.plot===null),'Original leading missing period lost');
      const segments=catalog.series.filter(s=>s.source_id.includes('ntpc') && s.entity==='新北市' && s.indicator==='藏書冊數');
      assert.equal(segments.length,2,'2010 collection-definition boundary was joined');
      assert(segments.every(s=>s.years.every(y=>y<2010)||s.years.every(y=>y>=2010)));
    } else {
      assert.equal(records.length,12,'Complete source monthly row must retain all twelve periods');
      assert.deepEqual(records.map(r=>r.month),Array.from({length:12},(_,i)=>i+1));
    }
    if(output)await page.screenshot({path:path.join(output,profileId+'-390.png'),fullPage:true});
    newProfileChecks.push({profile:profileId,records:records.length,source_links_checked:actual.length});
  }
  await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('#result').waitFor({state:'visible'});
  const beforeBatch=requests.filter(u=>u.endsWith(batchEntry.catalog_url)).length;
  await page.locator('#source-batch-links a').click();await page.locator('#source-batch').waitFor({state:'visible'});
  assert.equal(await page.locator('#batch-records tr').count(),24);assert(new URL(page.url()).searchParams.get('batch')==='ncl94-statistics');
  assert.equal(requests.filter(u=>u.endsWith(batchEntry.catalog_url)).length,beforeBatch+1,'Entry should load source batch on demand');
  await page.selectOption('#mode','profile');await page.locator('#result').waitFor({state:'visible'});
  assert.equal(await page.locator('#batch-records tr').count(),0,'Switch to charts retained batch rows');
  assert(await page.locator('#source-batch').isHidden());
  const beforeCachedBatch=requests.length;await page.selectOption('#mode','batch');await page.locator('#source-batch').waitFor({state:'visible'});
  assert.equal(requests.length,beforeCachedBatch,'Returning to batch should reuse its cache');
  await page.goto(base+'?batch=not-registered',{waitUntil:'domcontentloaded'});await page.locator('#status.is-error').waitFor();
  assert.equal(await page.locator('#batch-records tr').count(),0,'Unknown source batch retained data');assert.equal(await page.locator('.data-line').count(),0);
  assert.deepEqual(interactionErrors,[],'Switching and deep links emitted browser errors');
  await page.route('**/data/*.json',r=>r.abort());
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#status.is-error').waitFor();assert.equal(await page.locator('.plot-point').count(),0,'Failed load retained old data');assert(await page.locator('#retry').isVisible());
  await context.close();
  console.log(JSON.stringify({passed:true,mobile_and_desktop:results,source_batches:batchResults,new_source_profiles:newProfileChecks,checked_cases:['exact 2020–2024 interval','unresolved interval clears chart','incomplete period clears chart','series cache','monthly original gaps','dynamic official entry note','new complete source months and definition break','batch cold deep link and reload','24 exact batch raw values and official PDF locators','batch entry and mode switching with cache','unknown batch fails closed','network failure with retry'],isolated_headless:true}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));});
