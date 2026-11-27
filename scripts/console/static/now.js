/* 상황판 탭 렌더러 — app.js 의 공용 헬퍼($, esc, api, bar, win, dur, hhmm …)를 호출 시점에 참조한다. */
const openPh={},openRole={};
const QKO={queued:'대기',in_progress:'진행중',done:'완료',failed:'실패',review:'사후 검토',blocked:'막힘'};
const TKO={audit:'감사',watch:'감시'};
const ROLE_KO={steward:'비전 관리',planner:'버전 계획',designer:'설계',developer:'개발',verifier:'검증',auditor:'감사',deployer:'배포'};
const FLAG_KO={paused:'일시정지',skip:'건너뛰기',rerun:'재실행'};
const sep='<span class="sp">·</span>';
function stepsHtml(p,ph){const st=p.steps||[];if(!st.length)return '';
 const last=st[st.length-1],bad=st.filter(x=>x.bad),open=!!openPh[ph],t=x=>new Date(x.ts*1000).toLocaleTimeString('ko-KR',{hour12:false});
 const sum=`${esc(ph||'-')} 단계 · ${esc(last.text)}${bad.length?` · <span class="bd">실패 ${bad.length}</span>`:''}`;
 return `<div class="sm" data-tg="${esc(ph||'')}">${open?'▼':'▶'} ${sum}</div>`+(open?'<div class="sl">'+st.map((x,i)=>`<div class="${x.bad?'bd':i===st.length-1?'cu':''}">${t(x)} ${esc(x.text)}</div>`).join('')+'</div>':'')}
function linksHtml(o){const s=o.state,q=o.queue||{},p=o.progress||{};
 const L=[[o.decisions_open,'#dec','결정'],[p.review_waiting,'#rev','사후 검토'],[q.blocked_count,'#items?stage=failed','막힌 항목','bd'],[s.fails,'#items?stage=failed','실패','bd'],[s.units_done,'#items?stage=done','완료']]
  .filter(x=>x[0]>0).map(x=>`<a ${x[3]?`class="${x[3]}" `:''}href="${x[1]}">${x[2]} ${x[0]}</a>`);
 return L.length?`<div class="lks">${L.join(sep)}</div>`:''}
function flowHtml(o){
 const s=o.state,f=o.flags,p=o.progress||{},cur=p.stage||0;
 const el=ts=>ts?`<span class="el" data-since="${ts}">${dur(Date.now()/1000-ts)}</span>`:'-';
 const steps=STG.map((n,i)=>{const k=i+1,c=k<cur?'done':k===cur?'on':'';
  let sub='';
  if(k===1&&p.subs&&cur===1)sub='<div class="sub">'+Object.keys(SUBN).map(x=>{const v=p.subs[x];return `<span class="${v.state}">${v.state==='done'?'✔':v.state==='active'?'▶':'·'} ${SUBN[x]}</span>`}).join(' ')+'</div>';
  if(k===2&&p.design)sub=`<div class="sub">후보 ${p.design.new}</div>`;
  if(k===3&&p.units){const u=p.units;sub=`<div class="sub"><a href="#items">단위 ${u.done}/${u.total}</a></div><div class="bar thin"><i style="width:${pct(u.done,u.total)}%"></i></div>`}
  if(k===4&&p.deploy&&p.deploy.ok!=null)sub=`<div class="sub">${p.deploy.ok?'완료':p.deploy.ran?'실패':'생략'}</div>`;
  return `<div class="stp ${c}"><div class="no">${k}</div><div class="nm">${n}</div>${sub}</div>`}).join('<div class="ln"></div>');
 const ban=f.stop?`<div class="ban bad">중지됨${s.stop_reason?' — '+esc(s.stop_reason):''}</div>`:(f.pause||s.stop_reason==='pause_flag')?`<div class="ban warn">⏸ 일시중지됨 — ${f.pause&&s.stop_reason!=='pause_flag'?'현재 단계가 끝나는 지점에서 멈춥니다':'단계 경계에서 멈춰 있습니다'} (재개 버튼으로 이어서 진행)</div>`:s.stop_reason&&s.stop_reason!=='pacing'?`<div class="ban ${s.stop_reason==='failed'?'bad':'warn'}">${esc(RSN[s.stop_reason]||s.stop_reason)}${s.stop_cause?'<br>원인: '+esc(s.stop_cause):''}</div>`:'';
 const sf=p.sweep_fix&&s.phase!=='audit'?`<div class="ban warn">스윕 수정 라운드 ${p.sweep_fix.attempt}/${p.sweep_fix.limit} · ${esc(p.sweep_fix.item)}${(p.sweep_fix.targets||[]).length?' · 대상 '+esc(p.sweep_fix.targets.join(', ')):''}</div>`:'';
 const d=p.design,wait=d?`후보 ${d.new} → 자체 승인 ${d.auto} · 결정 대기 ${d.user}`:'';
 return `<b>라운드 ${esc(s.round)}</b> <span class="tag">${cur?'현재 '+cur+'/4':esc(s.phase||'-')}</span>${p.inferred?' <span class="mut">(로그 추정)</span>':''}
 <div class="mut">시작 ${hhmm(p.round_started)} · 경과 ${el(p.round_started)}${s.phase?' · '+esc(s.phase)+' 단계 '+el(p.phase_started):''}</div>
 <div class="flow">${steps}</div>${stepsHtml(p,s.phase)}${ban}${sf}${wait?`<div class="mut">${wait}</div>`:''}${linksHtml(o)}`}
function tickEl(){document.querySelectorAll('[data-until]').forEach(e=>{const r=Number(e.dataset.until)-Date.now()/1000;e.textContent=r>0?'남은 시간 '+dur(r):'곧 재개'});document.querySelectorAll('[data-since]').forEach(e=>{e.textContent=dur(Date.now()/1000-Number(e.dataset.since))})}
function iniRow(i){return `<div class="row"><span>${esc(i.title)} <span class="tag">${esc(i.status)}</span></span><span>${i.done}/${i.total}</span></div><div class="bar thin"><i style="width:${pct(i.done,i.total)}%"></i></div>`}
function relHtml(r){
 if(!r)return'';const tot=r.initiatives.reduce((a,i)=>a+i.total,0),dn=r.initiatives.reduce((a,i)=>a+i.done,0);
 const ph=r.phases||[],inPh=new Set(ph.flatMap(p=>p.initiatives.map(i=>i.id))),rest=r.initiatives.filter(i=>!inPh.has(i.id));
 const cur=ph.find(p=>p.active);
 return `<div class="row"><b>${esc(r.version)} · ${esc(r.title)}</b><span class="tag">${esc(r.status)}</span></div>
 ${r.goal?`<div class="mut">목표: ${esc(r.goal)}</div>`:'<div class="mut">목표·단계 미설계 — 다음 감사/버전 계획 단계에서 생성됩니다</div>'}
 ${cur?`<div class="mut">현재 진행: <b>${esc(cur.id)}. ${esc(cur.title)}</b></div>`:''}
 ${bar('범위 전체',dn,tot,dn+' / '+tot+'건')}`
 +ph.map(p=>`<div class="row"><b>${esc(p.id)}. ${esc(p.title)}</b><span>${p.active?'<span class="tag">진행 중</span> ':p.total&&p.done>=p.total?'<span class="tag">완료</span> ':''}${p.done}/${p.total}</span></div><div class="bar thin"><i style="width:${pct(p.done,p.total)}%"></i></div>`+p.initiatives.map(i=>`<div class="sub2 mut">${iniRow(i)}</div>`).join('')).join('')
 +(rest.length?(ph.length?'<div class="mut">단계 밖</div>':'')+rest.map(i=>`<div class="sub2 mut">${iniRow(i)}</div>`).join(''):'')}
function rolesHtml(rs){rs=rs||{};
 return '<b>역할 패널</b> <span class="mut">행을 누르면 제어 버튼</span>'+Object.keys(ROLE_KO).map(r=>{const f=rs[r]||{},on=Object.keys(FLAG_KO).filter(k=>f[k]);
  return `<div class="rr${openRole[r]?' open':''}" data-rr="${r}"><span>${ROLE_KO[r]}</span><span>${on.length?on.map(k=>`<span class="tag warn">${FLAG_KO[k]}</span>`).join(' '):'<span class="mut">정상</span>'} <span class="mut">${openRole[r]?'▴':'▾'}</span></span></div>`
   +(openRole[r]?`<div class="rb">${Object.keys(FLAG_KO).map(k=>`<button class="b" data-rl="${r}" data-rf="${k}" data-rv="${f[k]?0:1}">${f[k]?FLAG_KO[k]+' 해제':FLAG_KO[k]}</button>`).join('')}</div>`:'')}).join('')+
 '<div class="mut">일시정지 = 해당 단계 진입 시 정지 · 건너뛰기 = 해제할 때까지 유지 · 재실행 = 다음 1회만</div>'}
function blockedHtml(q){return (q.blocked||[]).map(a=>`<div class="card"><div class="row"><span>${esc(a.id)} <span class="tag bad">막힘 · ${esc(a.kind||'-')}</span></span></div><div class="mut" style="white-space:pre-wrap;word-break:break-word">${esc(a.text)}</div><div class="mut">사유: ${esc(a.reason||'기록 없음(이전 버전 실패 — 시도 '+a.attempts+'회)')}</div><input id="fx-${esc(a.id)}" placeholder="의견·추가 지시(선택)" style="width:100%"><button class="b p" data-fa="requeue" data-fid="${esc(a.id)}">큐에 다시 넣기</button> <button class="b" data-fa="drop" data-fid="${esc(a.id)}">폐기</button></div>`).join('')}
function ago(ts){const m=Math.max(0,Math.round((Date.now()/1000-ts)/60));return m<1?'방금':m<60?m+'분 전':Math.round(m/60)+'시간 전'}
function renderNow(o){window.lastO=o;
 const s=o.state,f=o.flags,g=o.budget;
 const pacing=s.stop_reason==='pacing'||(!g.pacing_ok&&g.pacing_resume_at);
 const run=f.stop?'중지됨':f.pause||s.stop_reason==='pause_flag'?'⏸ 일시중지됨':pacing?'페이싱 대기':s.stop_reason==='failed'?'실패로 정지':['stopped','halted'].includes(s.phase)?'정지 상태':'실행 중 · '+(s.phase||'-');
 $('#flags').textContent=run;$('#dot').className='dot'+(f.stop?' bad':s.stop_reason==='failed'?' bad':f.pause||s.stop_reason==='pause_flag'||pacing?' warn':'');
 document.querySelector('[data-a=pause]').disabled=!!(f.pause||f.stop||s.stop_reason==='pause_flag');document.querySelector('[data-a=stop]').disabled=!!f.stop;
 document.querySelector('[data-a=resume]').disabled=!(f.pause||f.stop||s.stop_reason);
 const pw=$('#pw');
 pw.style.display=pacing?'':'none';
 if(pacing){const lifted=g.pacing_ok;pw.innerHTML=`${lifted?'페이싱 해제 — 재개 대기':'페이싱 대기 중'}<b>${g.pacing_resume_at?hhmm(g.pacing_resume_at)+' 재개':lifted?'한도 리셋됨 · 곧 재개':'재개 시각 계산 중'}</b><span ${g.pacing_resume_at?`data-until="${g.pacing_resume_at}"`:''}></span>${g.pacing_reason?`<div class="mut">${esc(g.pacing_reason)}</div>`:''}`}
 $('#rel').innerHTML=relHtml(o.release);$('#roles').innerHTML=rolesHtml(o.roles);
 $('#upd').textContent=new Date().toLocaleTimeString('ko-KR',{hour12:false});
 $('#st').innerHTML=flowHtml(o);
 const q=o.queue,b=q.by_stage,bk=blockedHtml(q);
 $('#bk').innerHTML=bk;$('#bk').classList.toggle('hid',!bk);
 $('#qu').innerHTML=`<b>큐 (자동 ${q.total}건)</b><div>${Object.entries(b).map(([k,v])=>`<span class="tag">${QKO[k]||k} ${v}</span> `).join('')}</div>
 <div class="mut">다음 실행: ${esc(q.next||'없음')}</div>`+q.attention.filter(a=>a.stage!=='review').map(a=>`<div class="row"><span>${esc(a.id)} <span class="tag">${QKO[a.stage]||a.stage}</span></span></div><div class="mut">${esc(a.text)}</div>`).join('');
 $('#bu').innerHTML=`<b>예산·페이싱</b> <span class="mut">${g.observed_at?'관측 '+ago(g.observed_at):'관측 없음'}</span>${win('5시간 세션',pickWin(g,'five_hour'))}${win('7일 (균등 목표 '+Math.round(100*g.weekly_target)+'%)',pickWin(g,'seven_day'))}${g.pacing_ok||pacing?'':`<div class="mut">대기: ${esc(g.pacing_reason)}</div>`}`;
 const rv=q.attention.filter(a=>a.stage==='review');
 for(const[id,n]of[['#dn',o.decisions_open||0],['#rn',rv.length]]){const b=$(id);b.textContent=n>99?'99+':n;b.classList.toggle('hid',!n)}
 const rvh=rv.length?rv.map(a=>`<div class="card"><b>${esc(a.id)}</b> <span class="tag">사후 검토</span><div class="mut" style="white-space:pre-wrap;word-break:break-word">${esc(a.text)}</div>${pipeHtml(pipeMap[a.id])}<div class="mut">개발·검증 완료 — 브랜치 병합 전 확인 대기</div><button class="b" data-it="${esc(a.id)}">상세 ▾</button> <button class="b p" data-rv="${esc(a.id)}" data-ra="done">확인 완료</button> <button class="b" data-rv="${esc(a.id)}" data-ra="rework">재작업</button><div id="dt-${esc(a.id)}"></div></div>`).join(''):'<div class="card mut">검토 대기 항목 없음</div>';
 if(rvh!==window.lastRv){window.lastRv=rvh;$('#rv').innerHTML=rvh;reopenIt()}
}
function renderTimers(){
 $('#tm').innerHTML=Object.entries(timers).map(([k,v])=>{const n=k.replace('runpulse-','');return `<div class="row"><span>${TKO[n]||n} <span class="tag">${esc(v.active||'?')}</span></span><span data-next="${esc(v.next||0)}"></span></div>`}).join('');
 tickTimers()}
function tickTimers(){document.querySelectorAll('[data-next]').forEach(e=>{e.textContent=left(Number(e.dataset.next)*1e6)})}
function buildSettings(){
 $('#tmset').innerHTML=['runpulse-audit','runpulse-watch'].map(t=>{const n=t.replace('runpulse-','');return `<label for="iv-${t}">${TKO[n]} 간격(분, 10~1440)</label><input type="number" min="10" max="1440" placeholder="분" id="iv-${t}"><button class="b" data-iv="${t}">적용</button>`}).join('');
 $('#tun').innerHTML=Object.entries(TUN).map(([k,l])=>`<label for="tn-${k}">${l}</label><input type="number" step="any" id="tn-${k}"><button class="b" data-tn="${k}">적용</button>`).join('')}
