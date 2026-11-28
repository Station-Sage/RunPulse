const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TOG={SESSION_PACING_ENABLED:['5시간 세션 페이싱','사용률 80% 이상이면 리셋까지 대기'],WEEKLY_PACING_ENABLED:['주간 페이싱','7일 사용률이 균등 목표선을 넘으면 대기']};
const TUN={AUDIT_TOOL_CALLS_PER_ROUND:'감사 라운드당 도구 호출 수'};
let timers={},tab='now',typing=false,drafts={};
async function api(p,body){
 const o=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};
 const r=await fetch(p,o);let j={};try{j=await r.json()}catch(e){}
 if(!r.ok&&body)toast(j.error||j.reason||'실패 '+r.status,true);return j}
function toast(t,bad){const m=$('#msg');m.textContent=t;m.style.background=bad?'#7f1d1d':'#065f46';m.style.display='block';setTimeout(()=>m.style.display='none',2500)}
function fmt(ts){return ts?new Date(ts*1000).toLocaleString('ko-KR',{hour12:false}):'-'}
function left(us){const t=Number(us)/1e6;if(!t)return'-';const s=Math.round(t-Date.now()/1000);if(s<=0)return'곧 실행';return Math.floor(s/60)+'분 '+s%60+'초 후'}
function pct(a,b){return b?Math.min(100,Math.round(100*a/b)):0}
function bar(l,a,b,txt,prog){const p=pct(a,b);return `<div class="row"><span>${l}</span><span>${txt||a+' / '+b}</span></div><div class="bar ${prog?'':p>=90?'bad':p>=75?'warn':''}"><i style="width:${p}%"></i></div>`}
function win(l,w){if(!w)return bar(l,0,100,'데이터 없음');if(w.expired)return bar(l,0,100,'리셋됨 ('+hhmm(w.resetsAt)+') · 새 창 대기');if(w.utilization==null)return bar(l,0,100,'사용률 관측 없음 · 리셋 '+hhmm(w.resetsAt));const u=Math.round(100*w.utilization);return bar(l,u,100,u+'% · 리셋 '+hhmm(w.resetsAt))}
function pickWin(g,k){const now=Date.now()/1000;let old=null;for(const r of [g[k],g.five_hour,g.seven_day]){let w=r&&(r.rateLimitType===k?r:null);const nw=r&&(r.unifiedWindows||{})[k];if(nw&&(!w||w.utilization==null))w=w?{...w,...nw}:nw;if(!w)continue;if(w.resetsAt>now)return w;old=old||w}return old&&{...old,expired:1}}
const RSN={pacing:'페이싱 대기',pause_flag:'일시중지됨',failed:'실패로 정지 — 사람 확인 필요 (재개 버튼으로 이어감)',round_done:'라운드 완료 — 다음 감사 대기',step_cap:'단계 상한 — 자동 재개 대기',stop_flag:'중지됨',await_decision:'사용자 결정 대기',role_pause:'역할 일시정지',blocked:'환경 차단 — 사람 확인 필요 (원인 해소 후 재개)'};
const STG=['감사','설계','개발','테스트','반영'],SUBN={sweep:'스윕',audit:'관점 감사',review:'독립 검토'};
function dur(sec){sec=Math.max(0,Math.round(sec));const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60);return h?h+'시간 '+m+'분':m?m+'분 '+sec%60+'초':sec+'초'}
function hhmm(ts){return ts?new Date(ts*1000).toLocaleString('ko-KR',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}):'-'}
function sec(t,body){return body?`<div class="sec"><div class="st">${t}</div>${body}</div>`:''}
function lst(a){return a&&a.length?'<ul>'+a.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':''}
const revAsked={};
let revChain=Promise.resolve();
function askReviews(list){for(const d of list){if(d.status==='open'&&['split_decision','verify_decision'].includes(d.kind)&&!d.review_source&&!revAsked[d.id]){revAsked[d.id]=1;revChain=revChain.then(()=>api('/api/decisions/'+d.id+'/review',{})).then(r=>{if(r&&r.source==='pending'){setTimeout(()=>{delete revAsked[d.id]},60000)}else load()}).catch(()=>{delete revAsked[d.id]})}}}
function renderDec(list){
 askReviews(list);
 $('#dl').innerHTML=list.length?list.map(d=>{
  const open=d.status==='open',waiting=d.status==='redo';
  const chg=!open&&!waiting&&!['initiative','vision'].includes(d.kind)&&!(d.kind==='deploy_failed'&&d.status==='applied');
  const act=open||chg;
  const f=typeof d.finding==='object'&&d.finding?d.finding:{impact:d.finding||''};
  const rec=d.recommendation;
  return `<div class="card"><b>${esc(d.summary||d.id)}</b> <span class="tag${waiting?' warn':''}">${waiting?'재제안 대기':esc(d.status)}</span> <span class="mut">${esc(d.id)}</span>
  ${sec('검토안',(['split_decision','verify_decision'].includes(d.kind)?(d.review_source==='agent'?'<span class="tag ok">에이전트 검토</span> ':d.review_source==='rule'?'<span class="tag warn">규칙 기반 추정</span> ':open?'<span class="tag">에이전트 검토 중…</span> ':''):'')+esc(d.review||''))}
  ${sec('무엇이 문제인가',(f.perspective?`<span class="tag">${esc(f.perspective)}</span> `:'')+esc(f.impact||''))}
  ${sec('제안된 수정',esc(f.fix||''))}
  ${sec('발견된 곳',lst(f.cells))}
  ${sec('결정이 필요한 이유',esc(d.why||''))}
  ${sec('영향 범위',lst(d.scope))}
  ${sec('검증 방법',lst(d.verify))}
  <div class="st">선택지</div>
  ${act?`<textarea class="tx" id="tx-${esc(d.id)}" placeholder="${d.kind==='deploy_failed'?'의견·메모 (선택)':'의견·새 verify 커맨드·재정의 지시 (선택)'}">${esc(d.text||'')}</textarea><div class="row"><button class="b" data-dn="${esc(d.id)}">의견 저장</button><span class="mut" id="ns-${esc(d.id)}">${d.text?'저장된 의견이 입력란에 표시됩니다':'저장된 의견 없음'}</span></div>`:''}
  ${!act&&d.text?`<div class="mut">내 의견: ${esc(d.text)}</div>`:''}
  ${(d.options||[]).map(o=>`<div class="opt${o.key===rec?' rec':''}${!open&&o.key===d.choice?' sel':''}"><b>${esc(o.key)}. ${esc(o.name)}</b>${o.key===rec?' <span class="tag ok">추천</span>':''}${!open&&o.key===d.choice?' <span class="tag ok">내 선택</span>':''}<div class="pro">+ ${esc(o.pros)}</div><div class="con">- ${esc(o.cons)}</div>${o.review?`<div class="mut">검토: ${esc(o.review)}</div>`:''}${!open&&o.key===d.choice&&d.text?`<div class="mut" id="op-${esc(d.id)}" style="white-space:pre-wrap;word-break:break-word">내 의견: ${esc(d.text)}</div>`:''}
   ${act&&!(chg&&o.key===d.choice)?`<button class="b p" data-dc="${esc(d.id)}" data-ch="${esc(o.key)}">${open?'이 안으로 진행':'이 안으로 변경'}</button>`:''}</div>`).join('')||'<div class="mut">선택지 없음 — "다른 제안 받기"로 상세 안을 요청</div>'}
  <div class="mut">${rec?'추천: '+esc(rec)+(d.recommend_why?' — '+esc(d.recommend_why)+' (제안일 뿐 자동 적용되지 않습니다)':''):'추천 없음 (분류기가 추천을 내지 않음)'}</div>
  ${sec('되돌리는 방법',esc(d.revert||''))}
  ${open&&d.kind!=='deploy_failed'?`<button class="b" data-dc="${esc(d.id)}" data-ch="redo">다른 제안 받기</button>`:open?'<div class="mut">선택지에서 고르세요 — 이 카드는 재제안이 없습니다</div>':waiting?'<div class="mut">다른 제안을 준비 중 — 새 안이 올라오면 다시 표시됩니다</div>':`<div class="mut">선택: ${esc(d.choice||'-')}${chg?' · 개발이 시작되기 전까지 다른 안으로 바꿀 수 있습니다':''}</div>`}</div>`}).join(''):'<div class="card mut">결정함이 비어 있음</div>'}
const ISTG={in_progress:'진행중',queued:'대기',needs_decision:'결정 필요',failed:'실패',review:'사후 검토',done:'완료'};
let openIt={},itHtml={},istage='';
const PSTEP=[['design','설계'],['develop','개발'],['test','테스트'],['commit','커밋'],['deploy','운영반영']];
function pipeHtml(x){if(!x||!x.steps)return'';
 return `<div class="pipe">${PSTEP.map(([k,n])=>`<span class="${x.running&&x.running_step===k?'run':x.steps[k]?'ok':'no'}">${x.running&&x.running_step===k?'⏳':x.steps[k]?'✔':'·'} ${n}</span>`).join(' ')}${x.running?' <span class="tag warn">진행중</span>':''}</div>`}
let pipeMap={};
function kv(t,v){return v?`<div class="row"><span class="mut">${t}</span><span style="text-align:right">${esc(v)}</span></div>`:''}
function detailHtml(d){
 const i=d.item,r=d.review,dc=d.decision,rp=d.report||{};
 if(dc)askReviews([dc]);
 const dcs=dc?`<div class="mut">${esc(dc.kind||'')} · ${esc(dc.status)}${dc.choice?' · 선택 '+esc(dc.choice):''}</div>${sec('검토안',(['split_decision','verify_decision'].includes(dc.kind)?(dc.review_source==='agent'?'<span class="tag ok">에이전트 검토</span> ':dc.review_source==='rule'?'<span class="tag warn">규칙 기반 추정</span> ':dc.status==='open'?'<span class="tag">에이전트 검토 중…</span> ':''):'')+esc(dc.review||''))}${sec('요약',esc(dc.summary||''))}${sec('결정 이유',esc(dc.why||''))}${dc.status==='open'?`<textarea class="tx" id="tx-${esc(dc.id)}" placeholder="의견 (선택)">${esc(dc.text||'')}</textarea><div class="row"><button class="b" data-dn="${esc(dc.id)}">의견 저장</button><span class="mut" id="ns-${esc(dc.id)}">${dc.text?'저장된 의견이 입력란에 표시됩니다':'저장된 의견 없음'}</span></div>`:sec('내 의견',esc(dc.text||''))}${(dc.options||[]).map(o=>`<div class="opt${o.key===dc.choice?' sel':''}${o.key===dc.recommendation?' rec':''}"><b>${esc(o.key)}. ${esc(o.name)}</b>${o.key===dc.recommendation?' <span class="tag ok">추천</span>':''}${o.key===dc.choice?' <span class="tag ok">선택</span>':''}${dc.status==='open'?`<div class="pro">+ ${esc(o.pros)}</div><div class="con">- ${esc(o.cons)}</div><button class="b p" data-dc="${esc(dc.id)}" data-ch="${esc(o.key)}">이 안으로 진행</button>`:''}</div>`).join('')}${dc.status==='open'&&dc.recommendation?`<div class="mut">추천: ${esc(dc.recommendation)}${dc.recommend_why?' — '+esc(dc.recommend_why)+' (제안일 뿐 자동 적용되지 않습니다)':''}</div>`:''}`:'<div class="mut">결정 기록 없음 — 사용자 결정 없이 자동 큐에 올라온 항목</div>';
 const runs=(d.runs||[]).map(x=>`<div class="mut">${fmt(x.ts)} · ${esc(x.outcome)} · ${x.num_turns??'-'}턴 · ${Math.round(x.duration_s||0)}초 · $${(x.cost_usd||0).toFixed(2)}</div>`).join('')||'<div class="mut">실행 기록 없음</div>';
 const tl=(d.timeline||[]).map(x=>`<div class="mut">${fmt(x.ts)} ${esc(x.kind)}${x.round?' · 라운드 '+x.round:''}${x.result?' · '+esc(x.result):''}</div>`).join('');
 const au=(d.audit||[]).map(x=>`<div class="mut">${esc(x.ts)} ${esc(x.action)} ${esc(JSON.stringify(x.detail))}</div>`).join('');
 const rvw=['review','done'].includes(i.stage)?`<div class="st">사후 검토</div>${sec('검토 대상',esc(r.what))}${sec('검토 방법(verify)',lst(r.verify_cmds))}${sec('검토 경과',esc(r.how))}${sec('발견된 문제',r.problems.length?lst(r.problems):'<span class="pro">기록된 문제 없음</span>')}${sec('추가로 볼 것',lst(r.remaining))}`:'';
 const fc=i.stage==='failed'?failedCardHtml({id:i.id,kind:i.fail_kind,reason:i.fail_reason,text:i.full_text,attempts:i.attempts}):'';
 return `${fc}<div class="opt"><span class="tag">${ISTG[i.stage]||esc(i.stage)}</span>${pipeHtml(pipeMap[i.id])} <span class="mut">시도 ${i.attempts}회${i.critical?' · critical':''}${i.resolution?' · '+esc(i.resolution):''}</span>
 ${sec('무엇인가',esc(i.full_text))}${sec('범위',lst(i.scope))}${sec('verify',lst(i.verify))}${i.deps.length?sec('선행 항목',esc(i.deps.join(', '))):''}
 <div class="st">어떻게 결정되었나</div>${dcs}
 <div class="st">어떻게 개발되었나</div>${runs}${tl?`<div class="sl">${tl}</div>`:''}${sec('최종 실행 보고',rp.report?`<pre>${esc(rp.report)}</pre>`:'')}${au?sec('콘솔 조작 이력',au):''}${rvw}</div>`}
async function toggleIt(id){
 const el=document.getElementById('dt-'+id);if(!el)return;
 if(openIt[id]){delete openIt[id];delete itHtml[id];el.innerHTML='';return}
 el.innerHTML='<div class="mut">불러오는 중…</div>';
 const d=await api('/api/item/'+encodeURIComponent(id));
 if(d&&d.item){openIt[id]=1;itHtml[id]=detailHtml(d);el.innerHTML=itHtml[id]}else el.innerHTML='<div class="mut">'+esc((d&&d.error)||'불러오기 실패')+'</div>'}
function renderItems(r){
 if(!r||!r.items)return;
 const c=r.counts;
 $('#ih').innerHTML=`<b>개발 항목 ${r.total}건 · 완료 ${r.done_pct}%</b><div class="bar" style="margin:6px 0"><i style="width:${r.done_pct}%"></i></div>`+Object.keys(ISTG).map(k=>`<a class="go tag${k==='failed'&&c[k]?' bad':''}${istage===k?' warn':''}" href="#items?stage=${k}">${ISTG[k]} ${c[k]||0}</a> `).join('')+(istage?` <a class="go" href="#items">필터 해제 ✕</a>`:'');
 pipeMap={};for(const it of r.items)pipeMap[it.id]=it;
 let cur='';const body=[];
 for(const it of r.items.filter(x=>!istage||x.stage===istage)){
  if(it.stage!==cur){cur=it.stage;body.push(`<div class="st">${ISTG[cur]||esc(cur)} (${c[cur]||0})</div>`)}
  body.push(`<div class="card" style="padding:8px 12px"><div class="row" data-it="${esc(it.id)}" style="cursor:pointer"><span><b>${esc(it.id)}</b> <span class="tag${it.stage==='failed'?' bad':''}">${ISTG[it.stage]||esc(it.stage)}</span></span><span class="mut">${it.stage==='queued'?`<button data-qid="${esc(it.id)}" data-qa="up" title="한 칸 위로">↑</button> <button data-qid="${esc(it.id)}" data-qa="top" title="맨 앞으로">맨 위</button> `:''}▾</span></div>${pipeHtml(it)}<div class="mut">${esc(it.text)}</div><div id="dt-${esc(it.id)}"></div></div>`)}
 $('#il').innerHTML=body.length?body.join(''):`<div class="card mut">${istage?esc(ISTG[istage]||istage)+' 상태의 항목이 없습니다.':'항목이 없습니다.'}</div>`;
 reopenIt()}
function reopenIt(){for(const id of Object.keys(openIt)){const el=document.getElementById('dt-'+id);if(el&&!el.innerHTML){if(itHtml[id])el.innerHTML=itHtml[id];else{delete openIt[id];toggleIt(id)}}}}
async function loadItems(){const r=await api('/api/items');if(r&&r.items){pipeMap={};for(const it of r.items)pipeMap[it.id]=it}if(tab==='items')renderItems(r)}
function showLog(l){
 if(!Array.isArray(l))return;const e=$('#log');const sel=getSelection();if(sel&&!sel.isCollapsed&&e.contains(sel.anchorNode))return;const top=e.scrollTop<24;
 e.textContent=l.slice(-60).reverse().join('\n');if(top)e.scrollTop=0}
async function pollLog(){if(tab!=='log'||document.hidden)return;showLog(await api('/api/log'));$('#logst').textContent='실시간 · '+new Date().toLocaleTimeString('ko-KR',{hour12:false})}
const TABS=['now','log','items','dec','rev'];
function fitLog(){const l=$('#log');if(!l||$('#t-log').classList.contains('hid'))return;l.style.height=Math.max(200,innerHeight-l.getBoundingClientRect().top-scrollY-62)+'px'}
addEventListener('resize',fitLog);
function setTab(k){
 if(!TABS.includes(k))k='now';tab=k;
 document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.t===k));
 for(const x of TABS)$('#t-'+x).classList.toggle('hid',x!==k);
 fitLog();if(k==='log')pollLog();if(k==='items')loadItems()}
function tabFromHash(){const[h,q]=location.hash.slice(1).split('?');istage=(new URLSearchParams(q||'').get('stage'))||'';return h==='todo'?'dec':h}
async function load(){
 const [o,d,l,t,tv]=await Promise.all([api('/api/overview'),api('/api/decisions'),api('/api/log'),api('/api/timers'),api('/api/tunables')]);
 if(o.state)renderNow(o);
 if(Array.isArray(d))renderDec(d);
 for(const[k,v]of Object.entries(drafts)){const e=document.getElementById(k);if(e&&e.value!==v)e.value=v}
 showLog(l);loadItems();
 if(t&&typeof t==='object'){timers=t;renderTimers()}
 if(tv)for(const[k,v]of Object.entries(tv)){const g=$('#tg-'+k);if(g){g.dataset.on=v?'1':'0';g.textContent=v?'켜짐':'꺼짐';g.classList.toggle('p',!!v)}}
 if(tv&&!typing)for(const[k,v]of Object.entries(tv)){const e=$('#tn-'+k);if(e&&document.activeElement!==e&&!e.value)e.value=v}}
document.addEventListener('toggle',e=>{const d=e.target.closest&&e.target.closest('[data-tmd]');if(d)openTm[d.dataset.tmd]=d.open},true);
document.addEventListener('click',async e=>{
 const tm=e.target.closest('[data-tm]');if(tm){const on=tm.dataset.on!=='1';if(!on&&tm.dataset.tm==='watch'&&!confirm('감시를 끄면 멈춤·이상 상태를 점검하지 않습니다. 끌까요?'))return;
  tm.disabled=true;const r=await api('/api/timer',{name:'runpulse-'+tm.dataset.tm,on});if(r&&r.ok===false)alert(r.error||'실패');load();return}
 const rr=e.target.closest('[data-rr]');if(rr){openRole[rr.dataset.rr]=!openRole[rr.dataset.rr];if(window.lastO)renderNow(window.lastO);return}
 const g=e.target.closest('[data-tg]');if(g){openPh[g.dataset.tg]=!openPh[g.dataset.tg];if(window.lastO)renderNow(window.lastO);return}
 const it=e.target.closest('[data-it]');if(it&&!e.target.closest('button')){toggleIt(it.dataset.it);return}
 const t=e.target.closest('button');if(!t)return;
 if(t.dataset.t){history.replaceState(null,'','#'+t.dataset.t);setTab(t.dataset.t);return}
 let r;
 if(t.dataset.a){if(t.dataset.a==='stop'&&!confirm('즉시 중지할까요? 실행 중 프로세스를 종료합니다.'))return;r=await api('/api/control',{action:t.dataset.a})}
 else if(t.dataset.rl){r=await api('/api/roles',{role:t.dataset.rl,flag:t.dataset.rf,value:t.dataset.rv==='1'})}
 else if(t.dataset.tg2){r=await api('/api/tunables',{values:{[t.dataset.tg2]:t.dataset.on==='1'?0:1}})}
 else if(t.dataset.tn){r=await api('/api/tunables',{values:{[t.dataset.tn]:Number($('#tn-'+t.dataset.tn).value)}})}
 else if(t.dataset.dc){r=await api('/api/decisions/'+t.dataset.dc,{choice:t.dataset.ch,text:(($('#tx-'+t.dataset.dc)||{}).value||'')})}
 else if(t.dataset.dn){const v=(($('#tx-'+t.dataset.dn)||{}).value||'');r=await api('/api/decisions/'+t.dataset.dn+'/note',{text:v});if(r&&r.ok){delete drafts['tx-'+t.dataset.dn];const m=$('#ns-'+t.dataset.dn);const o=$('#op-'+t.dataset.dn);if(o)o.textContent=v.trim()?'내 의견: '+v.trim():'';if(m)m.textContent=v.trim()?'저장됨: '+v.trim().slice(0,60):'의견 삭제됨';toast(v.trim()?'의견 저장됨':'의견 삭제됨');return}}
 else if(t.dataset.fid){if(t.dataset.fa==='drop'&&!confirm('폐기할까요?'))return;r=await api('/api/failed/'+t.dataset.fid,{action:t.dataset.fa,text:(($('#fx-'+t.dataset.fid)||{}).value||'')})}
 else if(t.dataset.qid){r=await api('/api/queued/'+t.dataset.qid,{action:t.dataset.qa})}
 else if(t.dataset.rv){if(t.dataset.ra==='rework'&&!confirm('재작업 큐로 되돌릴까요?'))return;r=await api('/api/review/'+t.dataset.rv,{action:t.dataset.ra})}
 else return;
 if(r&&r.ok){toast(t.dataset.fid&&t.dataset.fa==='requeue'?'의견을 지시로 추가하고 큐에 넣었습니다':({pause:'일시중지 요청됨 — 진행 로그에 기록',resume:'재개 요청됨',start:'시작 요청됨',stop:'즉시 중지됨'})[t.dataset.a]||'적용됨');for(const k of['tx-'+t.dataset.dc,'fx-'+t.dataset.fid])delete drafts[k]}else if(r&&r.error)toast(r.error);load()});
document.addEventListener('focusin',e=>{typing=e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'});
document.addEventListener('input',e=>{const i=e.target.id||'';if(/^(tx|fx)-/.test(i))drafts[i]=e.target.value});
buildSettings();setTab(tabFromHash());load();
addEventListener('hashchange',()=>{setTab(tabFromHash());if(tab==='items')loadItems()});document.addEventListener('visibilitychange',pollLog);
setInterval(()=>{if(!typing)load()},15000);setInterval(()=>{tickTimers();tickEl()},1000);setInterval(pollLog,3000);