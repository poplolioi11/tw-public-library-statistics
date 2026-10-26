/* Standalone headless browser checks; never attach to a user's browser. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(process.argv[2]||path.join(__dirname,'..')),skipMain=process.argv.includes('--skip-main');
 const options={headless:true};if(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE)options.executablePath=process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
 const browser=await chromium.launch(options),context=await browser.newContext({viewport:{width:1280,height:1050}}),page=await context.newPage(),errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));await page.route(/^https?:/,r=>{external.push(r.request().url());return r.abort()});
 const results=[];const open=async file=>{await page.goto('file://'+path.join(root,'site',file),{waitUntil:'load',timeout:90000})};
 try{
  await open('phase3.html');await page.waitForSelector('#plot-view svg circle');assert.equal(await page.locator('#profile').inputValue(),'national-ncl-book-loans-panel');assert((await page.locator('#plot-view svg path').count())>1);assert((await page.locator('#plot-view svg a[href^="https://"]').count())>1);
  results.push('P3 visible default SVG with official source links');
  await page.selectOption('#profile','national-ncl-count-panel');await page.selectOption('#plot-start','2019');await page.selectOption('#plot-end','2019');assert((await page.locator('#plot-series').inputValue()).includes('national-ncl-count-panel'));assert((await page.locator('#plot-view').innerText()).includes('113'));results.push('2019 interval chooses qualified older original panel');
  await page.selectOption('#plot-start','2018');await page.selectOption('#plot-end','2024');assert.equal(await page.locator('#plot-view svg').count(),0);assert((await page.locator('#plot-status').innerText()).includes('no_single_qualified_original_panel_covers_requested_scope'));results.push('2018-2024 refuses cross-edition splice');
  await page.selectOption('#profile','county-2023-nlpi-default');assert.equal(await page.locator('#plot-view svg').count(),0);assert((await page.locator('#plot-view').innerText()).includes('單期'));results.push('single period stays in table without invented trend');
  await page.click('#all-routes');assert((await page.locator('#matches').innerText()).replace(/,/g,'').includes('56496'));assert.equal(await page.locator('#rows tr').count(),50);await page.click('#next');assert((await page.locator('#page').innerText()).startsWith('2'));results.push('all 56496 routes accessible with pagination');
  await page.fill('#q','THIS_SEARCH_CANNOT_MATCH_XX999');await page.waitForTimeout(250);assert((await page.locator('#rows').innerText()).includes('不能據此判定官方沒有資料'));await page.fill('#q','');await page.waitForTimeout(250);
  for(const view of ['candidate_decisions','queries','series_edges']){await page.selectOption('#view',view);assert((await page.locator('#rows tr').count())>0)}results.push('all four table views and honest no-match state');
  await page.selectOption('#view','candidate_decisions');await page.selectOption('#profile','national-ncl-book-loans-panel');await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(root,'tmp/phase3/phase3-browser-desktop.png'),fullPage:false});await page.locator('#line-charts').screenshot({path:path.join(root,'tmp/phase3/phase3-browser-chart.png')});
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(root,'tmp/phase3/phase3-browser-mobile.png'),fullPage:false});assert((await page.locator('#plot-view svg').boundingBox()).width<=390);await page.setViewportSize({width:1280,height:1050});results.push('responsive source SVG fits mobile viewport');
  await open('phase2.html');await page.waitForSelector('#chart-view svg circle');assert((await page.locator('#chart-choice option').count())>=639);await page.fill('#chart-search','新竹');assert((await page.locator('#chart-choice option').count())>0);assert((await page.locator('#chart-view svg circle').count())>12);results.push('P2 complete 639-chart selector and monthly chart');
  await page.fill('#chart-search','NO_MATCH_XX999');assert.equal(await page.locator('#chart-view svg').count(),0);assert((await page.locator('#chart-view').innerText()).includes('完整原值'));results.push('P2 empty chart search preserves data notice');
  if(!skipMain){await open('index.html');await page.waitForSelector('.phase3-preview svg circle');assert((await page.locator('.phase3-preview a[href="phase3.html#line-charts"]').count())===1);results.push('main landing page contains real visible source SVG and chart link')}
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const report={status:'PASS',dataset_version:fs.readFileSync(path.join(root,'VERSION'),'utf8').trim(),browser:'Bundled Playwright Chromium; separate headless context',tests:results,page_errors:errors,external_requests:external,user_surface_touched:false,scope:'Actual page rendering, input filters, SVG and navigation controls. Not historical definition or source-quantity certification.'};
  fs.writeFileSync(path.join(root,'research/phase3-browser-review.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
