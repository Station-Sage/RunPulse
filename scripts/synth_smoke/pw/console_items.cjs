const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage();const errs=[];
p.on('pageerror',e=>errs.push(String(e)));
await p.goto('http://localhost:8799/#now');await p.waitForTimeout(1500);
const links=await p.$$eval('a[href^="#items"]',a=>a.map(x=>x.getAttribute('href')));
console.log('links',links);
await p.goto('http://localhost:8799/#items?stage=done');await p.reload();await p.waitForTimeout(1500);
console.log('pipe',await p.$$eval('.pipe',e=>e.length),'filter',await p.$$eval('a.go',a=>a.some(x=>x.textContent.includes('필터 해제'))));
console.log('stages',await p.$$eval('#il .tag',e=>[...new Set(e.map(x=>x.textContent))]).catch(()=>null));
await p.screenshot({path:'/tmp/items.png'});
console.log('errs',errs);await b.close()})()
