"""훈련 캘린더 공통 JS — week/month 뷰 공유 (H-1 스와이프, H-2 모달, H-3 툴팁 포함)."""
from __future__ import annotations

CALENDAR_JS = """<script>
if (!window.rpSaveEdit) {

  /* ── 네비게이션 ─────────────────────────────────────────────────── */
  window.rpNavTo = function(href, calUrl) {
    var el = document.getElementById('rp-calendar');
    if (!el) { window.location = href; return; }
    el.style.opacity = '0.5'; el.style.pointerEvents = 'none';
    fetch(calUrl).then(function(r) { return r.text(); })
      .then(function(html) {
        el.outerHTML = html;
        history.pushState({}, '', href);
        _rpPostNav();
      }).catch(function() { window.location = href; });
  };
  window.rpWeekNav = function(offset) {
    var el = document.getElementById('rp-calendar');
    if (!el) { window.location = '/training?week=' + offset; return; }
    el.style.opacity = '0.5'; el.style.pointerEvents = 'none';
    fetch('/training/calendar-partial?week=' + offset)
      .then(function(r) { return r.text(); })
      .then(function(html) {
        el.outerHTML = html;
        history.pushState({week: offset}, '', '/training?week=' + offset);
        _rpPostNav();
      }).catch(function() { window.location = '/training?week=' + offset; });
  };
  function _rpPostNav() {
    var nel = document.getElementById('rp-calendar');
    if (nel) { rpInitSwipe(nel); rpInitMonthTips(); }
  }
  window._rpRefreshCalendar = function() {
    var el = document.getElementById('rp-calendar');
    var view = el ? (el.dataset.view || 'week') : 'week';
    var off  = el ? parseInt(el.dataset.weekOffset || '0') : 0;
    if (view === 'week') {
      rpWeekNav(off);
    } else {
      rpNavTo('/training?view=month&week=' + off,
              '/training/calendar-partial?view=month&week=' + off);
    }
  };

  /* ── 인라인 편집 ────────────────────────────────────────────────── */
  window.rpEditTypeChange = function(wid, val) {
    var el = document.getElementById('ei-' + wid);
    if (el) el.style.display = val === 'interval' ? 'flex' : 'none';
  };
  window.rpCalcInterval = function(wid) {
    var rm = document.getElementById('er-' + wid);
    var pm = document.getElementById('epm-' + wid);
    var ep = document.getElementById('ep-' + wid);
    if (!rm || !ep) return;
    ep.textContent = '계산 중...';
    fetch('/training/workout/' + wid + '/interval-calc?rep_m=' + (rm.value || '1000') +
          '&pace=' + ((pm && pm.value) || '240'))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        ep.style.color = d.ok ? 'rgba(0,255,136,0.8)' : '#ff6b6b';
        ep.textContent = d.ok
          ? d.rationale + (d.warning ? ' \u26a0\ufe0f ' + d.warning : '')
          : (d.error || '계산 실패');
      }).catch(function() { ep.textContent = '요청 오류'; });
  };
  function _parsePaceSec(s) {
    if (!s) return null; s = s.trim(); if (!s) return null;
    if (s.indexOf(':') >= 0) {
      var p = s.split(':');
      return (parseInt(p[0]) || 0) * 60 + (parseInt(p[1]) || 0);
    }
    if (s.length >= 3)
      return (parseInt(s.slice(0, -2)) || 0) * 60 + (parseInt(s.slice(-2)) || 0);
    return parseInt(s) || null;
  }
  window.rpSaveEdit = function(wid) {
    var sel  = document.getElementById('et-'  + wid);
    var dist = document.getElementById('ed-'  + wid);
    var pmin = document.getElementById('epm-' + wid);
    var pmax = document.getElementById('epx-' + wid);
    var rm   = document.getElementById('er-'  + wid);
    var msg  = document.getElementById('em-'  + wid);
    var body = {
      workout_type:    sel  ? sel.value                        : null,
      distance_km:     dist && dist.value ? parseFloat(dist.value) : null,
      target_pace_min: pmin && pmin.value ? _parsePaceSec(pmin.value) : null,
      target_pace_max: pmax && pmax.value ? _parsePaceSec(pmax.value) : null,
      interval_rep_m:  rm   && rm.value   ? parseInt(rm.value) : null,
    };
    fetch('/training/workout/' + wid, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          if (msg) { msg.style.color = '#00ff88'; msg.textContent = '저장됨'; }
          setTimeout(window._rpRefreshCalendar, 700);
        } else {
          if (msg) { msg.style.color = '#ff6b6b'; msg.textContent = d.error || '저장 실패'; }
        }
      }).catch(function() {
        if (msg) { msg.style.color = '#ff6b6b'; msg.textContent = '요청 오류'; }
      });
  };

  /* ── H-1: 스와이프 ──────────────────────────────────────────────── */
  window.rpInitSwipe = function(el) {
    if (el._rpSwipeInited) return;
    el._rpSwipeInited = true;
    var tx = 0, ty = 0;
    var _hScrollEl = null, _hScrollStart = 0;
    el.addEventListener('touchstart', function(e) {
      tx = e.touches[0].clientX; ty = e.touches[0].clientY;
      /* 가로 스크롤 가능한 자식 요소를 찾아 초기 scrollLeft 기록 */
      _hScrollEl = null; _hScrollStart = 0;
      var t = e.target;
      while (t && t !== el) {
        if (t.scrollWidth > t.clientWidth + 2) {
          _hScrollEl = t; _hScrollStart = t.scrollLeft; break;
        }
        t = t.parentElement;
      }
    }, {passive: true});
    el.addEventListener('touchend', function(e) {
      /* 가로 스크롤이 실제로 발생했으면 스와이프 무시 */
      if (_hScrollEl && Math.abs(_hScrollEl.scrollLeft - _hScrollStart) > 5) return;
      var dx = e.changedTouches[0].clientX - tx;
      var dy = e.changedTouches[0].clientY - ty;
      if (Math.abs(dx) < 50 || Math.abs(dy) > Math.abs(dx)) return;
      var view = el.dataset.view || 'week';
      var off  = parseInt(el.dataset.weekOffset || '0');
      if (view === 'week') {
        rpWeekNav(dx < 0 ? off + 1 : off - 1);
      } else {
        var step = dx < 0 ? 4 : -4;
        rpNavTo('/training?view=month&week=' + (off + step),
                '/training/calendar-partial?view=month&week=' + (off + step));
      }
    }, {passive: true});
  };

  /* ── H-2: 워크아웃 모달 ─────────────────────────────────────────── */
  window._rpWid = null;
  window.rpOpenWorkout = function(el) {
    var d = el.dataset || {};
    window._rpWid = d.wid;
    var titleEl = document.getElementById('rp-wm-title');
    var infoEl  = document.getElementById('rp-wm-info');
    var msgEl   = document.getElementById('rp-wm-msg');
    var confBtn = document.getElementById('rp-wm-confirm');
    if (titleEl) titleEl.textContent = d.label || d.wtype || '';
    var parts = [];
    if (d.dist) parts.push(d.dist + 'km');
    if (d.paceMin && d.paceMax) parts.push(d.paceMin + '~' + d.paceMax + '/km');
    else if (d.paceMin) parts.push(d.paceMin + '/km');
    if (infoEl) infoEl.textContent = parts.join(' \u00b7 ');
    if (confBtn) confBtn.textContent = d.completed === '1' ? '\u21a9\ufe0f \uc644\ub8cc \ucde8\uc18c' : '\u2713 \uc644\ub8cc';
    if (msgEl) msgEl.textContent = '';
    var overlay = document.getElementById('rp-woverlay');
    var modal   = document.getElementById('rp-wmodal');
    if (overlay) overlay.style.display = 'block';
    if (modal) {
      modal.style.display = 'block';
      setTimeout(function() { modal.style.transform = 'translateY(0)'; }, 10);
    }
  };
  window.rpCloseWorkout = function() {
    var modal   = document.getElementById('rp-wmodal');
    var overlay = document.getElementById('rp-woverlay');
    if (modal) {
      modal.style.transform = 'translateY(100%)';
      setTimeout(function() { modal.style.display = 'none'; }, 300);
    }
    if (overlay) overlay.style.display = 'none';
  };
  window._rpWorkoutAction = function(endpoint, color, defaultMsg) {
    if (!window._rpWid) return;
    var msgEl = document.getElementById('rp-wm-msg');
    if (msgEl) { msgEl.style.color = 'rgba(255,255,255,0.6)'; msgEl.textContent = '\ucc98\ub9ac \uc911...'; }
    fetch('/training/workout/' + window._rpWid + '/' + endpoint, {
      method: 'POST', headers: {'Accept': 'application/json'}, body: new FormData()
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          var text = d.activity_summary || d.message || defaultMsg;
          if (msgEl) { msgEl.style.color = color; msgEl.textContent = text; }
          setTimeout(function() { rpCloseWorkout(); _rpRefreshCalendar(); }, 800);
        } else {
          if (msgEl) { msgEl.style.color = '#ff6b6b'; msgEl.textContent = d.error || '\ucc98\ub9ac \uc2e4\ud328'; }
        }
      }).catch(function() {
        if (msgEl) { msgEl.style.color = '#ff6b6b'; msgEl.textContent = '\uc694\uccad \uc624\ub958'; }
      });
  };
  window.rpWorkoutConfirm = function() { _rpWorkoutAction('toggle', '#00ff88', '\uc644\ub8cc \ucc98\ub9ac\ub428'); };
  window.rpWorkoutSkip    = function() { _rpWorkoutAction('skip',   '#ffaa00', '\uac74\ub108\ub9f8 \ucc98\ub9ac\ub428'); };
  window.rpWorkoutEdit    = function() {
    rpCloseWorkout();
    if (window._rpWid) {
      var ep = document.getElementById('edit-' + window._rpWid);
      if (ep) ep.style.display = ep.style.display === 'none' ? 'block' : 'none';
    }
  };

  /* ── H-3: 월간 카드 툴팁 (hover + 롱탭) ─────────────────────────── */
  window.rpInitMonthTips = function() {
    if (!document.getElementById('rp-tip')) {
      var tip = document.createElement('div');
      tip.id = 'rp-tip';
      tip.style.cssText = 'display:none;position:fixed;z-index:950;background:#1a1a2e;' +
        'border:1px solid rgba(0,212,255,0.3);border-radius:8px;padding:8px 12px;' +
        'font-size:12px;color:#fff;pointer-events:none;white-space:nowrap;' +
        'box-shadow:0 4px 12px rgba(0,0,0,0.4);';
      document.body.appendChild(tip);
      document.addEventListener('mousemove', function(e) {
        var t = document.getElementById('rp-tip');
        if (t && t.style.display !== 'none') {
          t.style.left = (e.clientX + 14) + 'px';
          t.style.top  = Math.max(8, e.clientY - 40) + 'px';
        }
      });
    }
    var tip = document.getElementById('rp-tip');
    document.querySelectorAll('[data-tip]').forEach(function(el) {
      if (el._rpTipInited) return;
      el._rpTipInited = true;
      /* 데스크탑: mouseenter/leave */
      el.addEventListener('mouseenter', function(e) {
        tip.textContent = el.dataset.tip;
        tip.style.display = 'block';
        tip.style.left = (e.clientX + 14) + 'px';
        tip.style.top  = Math.max(8, e.clientY - 40) + 'px';
      });
      el.addEventListener('mouseleave', function() { tip.style.display = 'none'; });
      /* 모바일: 200ms 롱탭 → 툴팁 미리보기 / 단순탭 → onclick이 모달 처리 (주간과 동일) */
      var _timer = null, _long = false;
      el.addEventListener('touchstart', function() {
        _long = false;
        _timer = setTimeout(function() {
          _long = true;
          tip.textContent = el.dataset.tip;
          tip.style.cssText = tip.style.cssText
            .replace(/display:[^;]+/, 'display:block')
            .replace(/left:[^;]+;?/, '').replace(/top:[^;]+;?/, '');
          tip.style.display = 'block';
          tip.style.left = '50%';
          tip.style.top  = '30%';
          tip.style.transform = 'translateX(-50%)';
          setTimeout(function() {
            tip.style.display = 'none';
            tip.style.transform = '';
          }, 2000);
        }, 200);
      }, {passive: true});
      el.addEventListener('touchend', function(e) {
        if (_timer) { clearTimeout(_timer); _timer = null; }
        if (_long) {
          /* 롱탭: 툴팁 표시 중 — 클릭 이벤트 억제 */
          e.preventDefault(); _long = false;
        }
        /* 단순탭: 합성 click 이벤트가 발생하여 onclick='rpOpenWorkout(this)'가 처리 */
      });
      el.addEventListener('click', function(e) { e.stopPropagation(); });
    });
  };

  /* ── 모달 DOM 생성 (1회) ─────────────────────────────────────────── */
  if (!document.getElementById('rp-wmodal')) {
    document.body.insertAdjacentHTML('beforeend',
      '<div id="rp-woverlay" onclick="rpCloseWorkout()" ' +
        'style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;' +
        'z-index:900;background:rgba(0,0,0,0.5);"></div>' +
      '<div id="rp-wmodal" ' +
        'style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:901;' +
        'background:#1a1a2e;border-radius:16px 16px 0 0;padding:20px;' +
        'transform:translateY(100%);transition:transform 0.3s ease;' +
        'max-height:70vh;overflow-y:auto;box-shadow:0 -4px 24px rgba(0,0,0,0.5);">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
          '<span id="rp-wm-title" style="font-size:16px;font-weight:bold;color:#fff;"></span>' +
          '<button onclick="rpCloseWorkout()" ' +
            'style="background:rgba(255,255,255,0.1);border:none;color:#fff;' +
            'width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:14px;">\u2715</button>' +
        '</div>' +
        '<div id="rp-wm-info" style="font-size:13px;color:rgba(255,255,255,0.7);margin-bottom:16px;"></div>' +
        '<div style="display:flex;gap:10px;margin-bottom:12px;">' +
          '<button id="rp-wm-confirm" onclick="rpWorkoutConfirm()" ' +
            'style="flex:1;background:rgba(0,255,136,0.2);border:1px solid rgba(0,255,136,0.4);' +
            'color:#00ff88;padding:10px;border-radius:10px;font-size:13px;cursor:pointer;">' +
            '\u2713 \uc644\ub8cc</button>' +
          '<button onclick="rpWorkoutSkip()" ' +
            'style="flex:1;background:rgba(255,170,0,0.2);border:1px solid rgba(255,170,0,0.4);' +
            'color:#ffaa00;padding:10px;border-radius:10px;font-size:13px;cursor:pointer;">' +
            '\u2715 \uc2a4\ud0b5</button>' +
          '<button onclick="rpWorkoutEdit()" ' +
            'style="flex:1;background:rgba(0,212,255,0.2);border:1px solid rgba(0,212,255,0.4);' +
            'color:#00d4ff;padding:10px;border-radius:10px;font-size:13px;cursor:pointer;">' +
            '\u270f\ufe0f \uc218\uc815</button>' +
        '</div>' +
        '<div id="rp-wm-msg" style="font-size:12px;min-height:16px;text-align:center;"></div>' +
      '</div>'
    );
  }

  /* ── 페이지 초기화 ────────────────────────────────────────────────── */
  (function() {
    var el = document.getElementById('rp-calendar');
    if (el) { rpInitSwipe(el); rpInitMonthTips(); }
  })();
}
</script>
"""
