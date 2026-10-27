// Run with NODE_PATH pointing to a Playwright installation. Uses isolated fixtures.
const {chromium} = require('playwright');
const {spawn, execFileSync} = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');

(async () => {
  const skill = path.resolve(__dirname, '..');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'qa-template-'));
  const qa = path.join(skill, 'scripts', 'qa.py');
  const port = 5197;
  const origin = `http://127.0.0.1:${port}`;
  let server, browser;
  try {
    execFileSync('python', [qa, '--project', dir, 'init']);
    fs.mkdirSync(path.join(dir, 'public'));
    fs.writeFileSync(path.join(dir, 'public', 'live.html'), '<input id="field" value="original">');
    fs.writeFileSync(path.join(dir, 'public', 'prd.html'), '<p>这是唯一正文短句。</p>');
    const cases = [{id:'T1', title:'示例', entries:[{id:'pc',label:'PC',url:origin+'/public/live.html'}], references:[{type:'image',label:'设计',entry:'pc',state:'编辑',url:origin+'/public/a.png'},{type:'prd',label:'原文',url:origin+'/public/prd.html',quote:'唯一正文短句'}], demo:[{action:'input',selector:'#field',value:'changed'}],checkpoints:[{id:'p1',title:'检查',mode:'human'}]}];
    fs.writeFileSync(path.join(dir, 'cases.json'), JSON.stringify(cases));
    execFileSync('python', [qa, '--project', dir, 'create', '--build', 'fixture']);
    server = spawn('python', [qa, '--project', dir, 'serve', '--port', String(port)], {windowsHide:true});
    await new Promise((resolve, reject) => { server.stdout.once('data', resolve); server.once('exit', () => reject(Error('server exited'))); });
    browser = await chromium.launch({headless:true, executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(origin);
    await page.waitForFunction(() => document.querySelector('#title').textContent.includes('T1'));
    assert.equal(await page.locator('#designState').inputValue(), '编辑');
    assert.equal(await page.locator('#refs option').count(), 2);
    const live = page.frameLocator('#live');
    await live.locator('#field').waitFor();
    await page.locator('#demoNext').click();
    assert.equal(await live.locator('#field').inputValue(), 'changed');
    await page.locator('#demoStop').click();
    assert.equal(await live.locator('#field').inputValue(), 'original');
    const popupPromise = page.waitForEvent('popup');
    await page.locator('#openPrd').click();
    const popup = await popupPromise; await popup.waitForLoadState();
    await page.locator('#locatePrd').click();
    assert.equal(await popup.evaluate(() => getSelection().toString()), '唯一正文短句');
    assert.deepEqual(errors, []);
    console.log('PASS: mapping, demo restoration, PRD selection, isolated initialization');
  } finally {
    if (browser) await browser.close();
    if (server) server.kill();
    if (path.dirname(dir) === path.resolve(os.tmpdir()) && path.basename(dir).startsWith('qa-template-')) fs.rmSync(dir, {recursive:true, force:true});
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
