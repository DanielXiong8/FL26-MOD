/* app.js — FL26 Face Builder V1 frontend logic (native JS, no framework) */
const $ = (s) => document.querySelector(s);
let CATALOG = null, CAND_JOB = null, SELECTED = null, PHOTOS = [];

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let msg = r.status;
    try { msg = (await r.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}

async function loadCatalog() {
  CATALOG = await api('/api/catalog');
  // reference players
  $('#ref').innerHTML = CATALOG.references.map(r =>
    `<option value="${r.pid}">${r.name} (${r.pid})</option>`).join('');
  // hair colors
  $('#hcolors').innerHTML = CATALOG.hair_colors.map(c =>
    `<div class="chip ${c.id === 2 ? 'on' : ''}" data-id="${c.id}" title="${c.name}"
      style="background:#${c.hex}"></div>`).join('');
  document.querySelectorAll('#hcolors .chip').forEach(ch =>
    ch.onclick = () => { document.querySelectorAll('#hcolors .chip').forEach(x => x.classList.remove('on'));
      ch.classList.add('on'); });
  // beards + brows
  $('#beard').innerHTML = CATALOG.beards.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
  $('#brow').innerHTML = CATALOG.eyebrows.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
  // teams: two-level league -> club navigation, ALL teams shown
  const teams = CATALOG.teams;
  const comps = [...new Set(teams.map(t => t.league))].sort((a, b) => {
    if (a === 'National Teams') return -1;
    if (b === 'National Teams') return 1;
    return a.localeCompare(b);
  });
  $('#comp').innerHTML = comps.map(c =>
    `<option value="${c}">${c} (${teams.filter(t => t.league === c).length})</option>`).join('');
  function fillTeams() {
    const lg = $('#comp').value;
    const list = teams.filter(t => t.league === lg)
      .sort((a, b) => (b.verified - a.verified) || a.display.localeCompare(b.display));
    $('#team').innerHTML = list.map(t =>
      `<option value="${t.id}">${t.verified ? '✅ ' : ''}${t.display} — ${t.roster_count}/33</option>`).join('');
    updRoster();
  }
  $('#comp').onchange = fillTeams;
  fillTeams();
  // default: China NT
  $('#comp').value = 'National Teams';
  fillTeams();
  $('#team').value = '10059';
  updRoster();
  // nations (China default 24)
  const china = CATALOG.nations.find(n => n.code === 24);
  $('#nat').innerHTML = CATALOG.nations.map(n =>
    `<option value="${n.code}" ${n.code === 24 ? 'selected' : ''}>${n.name}</option>`).join('');
  // attrs grid
  const NAMES = ['balance','reaction','acceleration','velocity','stamina','agility','shotpower',
    'standingtackle','slidingtackle','ballcontrol','dribble','shortpass','highpass','shot',
    'volley','mental_defensivepositioning','mental_vision'];
  $('#attrs').innerHTML = NAMES.map((n, i) =>
    `<label>${n.replace('mental_', 'm_')}<input type="number" data-i="${i}" value="80" min="1" max="127"></label>`).join('');
  document.querySelectorAll('#presetRow button').forEach(b => b.onclick = () => setPreset(b.dataset.p));
}

function updRoster() {
  const t = CATALOG.teams.find(x => x.id == $('#team').value);
  $('#roster').textContent = t ? `Current roster: ${t.roster_count} / 33` : '';
}

function setPreset(p) {
  const base = p === 'GK' ? [72,66,53,43,43,33,50,13,13,68,17,67,67,14,16,68,68]
    : p === 'DF' ? [70,74,78,82,80,72,60,88,85,66,62,70,72,55,58,88,80]
    : p === 'MF' ? [78,80,82,79,84,80,74,62,60,85,83,86,84,72,70,74,82]
    : p === 'Bal' ? Array(17).fill(75)
    : Array.from({length: 17}, (_, i) => 81 + i);
  document.querySelectorAll('#attrs input').forEach(inp => inp.value = base[+inp.dataset.i]);
}

// STEP 1 upload
const drop = $('#drop');
drop.onclick = () => $('#photos').click();
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove('over'); addPhotos(e.dataTransfer.files); };
$('#photos').onchange = (e) => addPhotos(e.target.files);
function addPhotos(fileList) {
  for (const f of fileList) {
    if (PHOTOS.length >= 3) break;
    const url = URL.createObjectURL(f);
    PHOTOS.push(f);
    const d = document.createElement('div');
    d.innerHTML = `<img src="${url}"><div class="primary-mark">${PHOTOS.length === 1 ? 'PRIMARY' : '#' + PHOTOS.length}</div>`;
    $('#thumbs').appendChild(d);
  }
  if (PHOTOS.length >= 3) $('#photos').disabled = true;
}

// STEP 2 candidates
$('#genBtn').onclick = async () => {
  if (!PHOTOS.length) return alert('先上传照片');
  $('#genBtn').disabled = true;
  const fd = new FormData();
  PHOTOS.forEach((f, i) => fd.append('files', f, f.name));
  fd.append('n', $('#n').value);
  fd.append('geometry', 'on'); // cards render on the PHOTO-shaped skeleton
  CAND_JOB = await api('/api/candidates', {method: 'POST', body: fd});
  listenProgress(CAND_JOB.id, (ev) => {
    $('#progressBar').textContent = `${ev.stage}: ${ev.state} ${ev.detail || ''}`;
  });
  const poll = setInterval(async () => {
    const j = await api('/api/job/' + CAND_JOB.id);
    if (j.state === 'PASS' || j.state === 'FAIL') {
      clearInterval(poll);
      $('#genBtn').disabled = false;
      if (j.state === 'FAIL') { $('#progressBar').textContent = 'FAIL: ' + (j.error || ''); return; }
      showCandidates();
    }
  }, 1500);
};

async function showCandidates() {
  const data = await api('/api/candidates/' + CAND_JOB.id);
  $('#s2').classList.remove('hidden');
  $('#cands').innerHTML = data.candidates.map(c => {
    const m = c.metrics || {};
    const rej = c.status === 'REJECT';
    const img = (c.game_preview && c.game_preview.front) ? c.game_preview.front : c.preview;
    const tag = (c.game_preview && c.game_preview.front) ? '游戏同款渲染' : '平面烘焙图';
    return `<div class="cand ${rej ? 'rej' : ''}" data-c="${c.name}">
      <img src="${img}">
      <div class="muted">${c.name} — ${c.status} <span class="tag">${tag}</span></div>
      <div class="muted">sim=${(m.similarity || m.sim || 0)}</div>
      ${c.game_preview ? `<div class="muted">视角:
        <a href="${c.game_preview.front}" target="_blank">正</a>
        <a href="${c.game_preview['45L']}" target="_blank">45L</a>
        <a href="${c.game_preview['45R']}" target="_blank">45R</a>
        <a href="${c.game_preview.side}" target="_blank">侧</a></div>` : ''}
      <button class="sel" ${rej ? 'disabled' : ''}>SELECT</button></div>`;
  }).join('');
  document.querySelectorAll('.cand button.sel').forEach(b => b.onclick = (e) => {
    document.querySelectorAll('.cand').forEach(x => x.classList.remove('sel'));
    e.target.closest('.cand').classList.add('sel');
    SELECTED = e.target.closest('.cand').dataset.c;
    $('#s3').classList.remove('hidden');
    $('#s3').scrollIntoView();
  });
}

// preview (game-equivalent face render)
$('#prevBtn').onclick = async () => {
  if (!CAND_JOB || !SELECTED) return alert('先在 ② 选择候选');
  const data = await api('/api/candidates/' + CAND_JOB.id);
  const c = data.candidates.find(x => x.name === SELECTED);
  if (!c || !c.baked) return alert('候选无 baked 纹理');
  const bakeAbs = decodeURIComponent(c.baked.replace('/api/file/', ''));
  $('#prevOut').classList.remove('hidden');
  $('#prevOut').textContent = 'Rendering...（Unity 后台渲染，勿关页面）';
  await fetch('/api/preview', {method: 'POST',
    body: (() => { const f = new FormData(); f.append('bake_png', bakeAbs); return f; })()});
  const poll = setInterval(async () => {
    const st = await (await fetch('/api/preview/state')).json();
    if (!st.running) {
      clearInterval(poll);
      if (st.result) {
        $('#prevOut').textContent = 'Preview ready（这就是游戏内显示效果）';
        $('#prevImgs').innerHTML = ['front', '45L', '45R', 'side'].map(v =>
          `<img src="${st.result[v]}">`).join('');
      } else {
        $('#prevOut').textContent = 'RENDER FAILED: ' + (st.error || '').slice(0, 300);
      }
    }
  }, 2000);
};

// BUILD
$('#buildBtn').onclick = async () => {
  const fd = new FormData();
  fd.append('reference_pid', 0); // ZERO-CLONE origin mode: no reference player, ever
  if (CAND_JOB && SELECTED) {
    // resolve the selected candidate's baked.png directly from the candidate endpoint
    try {
      const data = await api('/api/candidates/' + CAND_JOB.id);
      const c = data.candidates.find(x => x.name === SELECTED);
      if (c && c.baked) {
        // baked = '/api/file/<abs path>/baked.png' -> send absolute dir of baked.png
        const abs = decodeURIComponent(c.baked.replace('/api/file/', ''));
        fd.append('candidate_baked', abs);
      }
    } catch (e) { console.warn('candidate resolve failed', e); }
  }
  fd.append('name', $('#name').value);
  fd.append('position', $('#pos').value);
  fd.append('nat', $('#nat').value);
  fd.append('team_id', $('#team').value);
  fd.append('jersey', $('#jersey').value);
  fd.append('hair_color_id', document.querySelector('#hcolors .chip.on').dataset.id);
  fd.append('beard_enabled', $('#beardOn').checked);
  fd.append('beard_style_id', $('#beard').value);
  fd.append('eyebrow_index', $('#brow').value);
  fd.append('skin_tone', 6);
  fd.append('face_texture_id', 0); // auto-allocate EA slot (b1 10-15)
  // EXPERIMENTAL: MICA geometry warp (default off = device-proven texture-only)
  fd.append('geometry', $('#geoOn') && $('#geoOn').checked ? 'on' : 'off');
  const attrs = [...document.querySelectorAll('#attrs input')].map(i => i.value).join(',');
  fd.append('attrs', attrs);
  $('#buildBtn').disabled = true;
  const job = await api('/api/build', {method: 'POST', body: fd});
  listenProgress(job.id, (ev) => {
    $('#buildOut').textContent += `${ev.stage}: ${ev.state} ${ev.detail || ''}\n`;
  });
  const poll = setInterval(async () => {
    const j = await api('/api/job/' + job.id);
    if (j.state === 'PASS') {
      clearInterval(poll); $('#buildBtn').disabled = false;
      const r = j.result;
      $('#buildOut').textContent += `\nBUILD PASS ✓\nAPK: ${r.apk}\nPID: ${r.pid} | jersey ${r.jersey}\nSHA256: ${r.sha256}\nsize: ${r.size}`;
      const ib = document.createElement('button');
      ib.className = 'primary'; ib.textContent = '⑧ INSTALL TO DEVICE';
      ib.onclick = async () => {
        ib.disabled = true;
        const res = await api('/api/install/' + job.id, {method: 'POST'});
        $('#buildOut').textContent += '\nINSTALL: ' + JSON.stringify(res);
      };
      $('#buildOut').appendChild(ib);
    } else if (j.state === 'FAIL') {
      clearInterval(poll); $('#buildBtn').disabled = false;
      $('#buildOut').textContent += '\nBUILD FAILED: ' + (j.error || 'unknown');
    }
  }, 1500);
};

// roster manager
$('#expBtn').onclick = async () => {
  $('#mOut').textContent = 'exporting...';
  const r = await api('/api/roster/export', {method: 'POST'});
  $('#mOut').textContent = 'exported -> ' + r.dir;
};
$('#impBtn').onclick = async () => {
  const fd = new FormData();
  fd.append('pid', $('#mPid').value);
  fd.append('to_team', 10059);
  fd.append('jersey', $('#mJersey').value);
  try {
    const r = await api('/api/roster/move', {method: 'POST', body: fd});
    $('#mOut').textContent += '\n' + (r.msg || JSON.stringify(r));
  } catch (e) { $('#mOut').textContent += '\nERROR: ' + e.message; }
};

function listenProgress(jobId, cb) {
  const es = new EventSource('/api/progress?job_id=' + jobId);
  es.onmessage = (e) => { try { cb(JSON.parse(e.data)); } catch (err) {} };
}

loadCatalog();
