const API = "/api";

function escapeHtml(s){ return s.replace(/[&<>]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

/* ---------------- Tabs ---------------- */
document.querySelectorAll("nav.tabs button").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    document.querySelectorAll("nav.tabs button").forEach(b=>b.classList.remove("active"));
    document.querySelectorAll("section.panel").forEach(p=>p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-"+btn.dataset.tab).classList.add("active");
  });
});

/* ---------------- Chat ---------------- */
const chatLog = document.getElementById("chatLog");
function addMessage(role, html){
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.innerHTML = html;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}
function renderAnswer(text){
  const parts = text.split(/```[a-z]*\n?/);
  return parts.map((p,i)=> i % 2 === 1 ? `<pre>${escapeHtml(p)}</pre>` : escapeHtml(p).replace(/\n/g,"<br>")).join("");
}

document.getElementById("chatForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const q = input.value.trim();
  if(!q) return;
  input.value = "";
  addMessage("user", escapeHtml(q));
  const loadingEl = addMessage("assistant", "Thinking…");
  try{
    const res = await fetch(`${API}/chat`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ message: q })
    });
    if(!res.ok) throw new Error(await res.text());
    const data = await res.json();
    loadingEl.innerHTML = renderAnswer(data.answer);
    if(data.sources && data.sources.length){
      const src = document.createElement("div");
      src.className = "sources";
      src.innerHTML = `<details><summary>Notes retrieved (${data.sources.length})</summary><ul>${data.sources.map(s=>`<li>${escapeHtml(s)}</li>`).join("")}</ul></details>`;
      loadingEl.appendChild(src);
    }
  }catch(err){
    loadingEl.textContent = "Couldn't reach the backend just now. Check it's running and try again.";
  }
});

/* ---------------- Quiz ---------------- */
const topicGrid = document.getElementById("topicGrid");
let selectedTopic = null;

async function loadTopics(){
  try{
    const res = await fetch(`${API}/topics`);
    const data = await res.json();
    data.topics.forEach(title=>{
      const chip = document.createElement("button");
      chip.className = "topic-chip";
      chip.textContent = title;
      chip.addEventListener("click", ()=>{
        selectedTopic = title;
        document.querySelectorAll(".topic-chip").forEach(c=>c.classList.remove("selected"));
        chip.classList.add("selected");
      });
      topicGrid.appendChild(chip);
    });
  }catch(err){
    topicGrid.innerHTML = `<p class="status">Couldn't load topics — is the backend running?</p>`;
  }
}
loadTopics();

let quizState = null;
document.getElementById("startQuizBtn").addEventListener("click", async ()=>{
  const area = document.getElementById("quizArea");
  if(!selectedTopic){ area.innerHTML = `<p class="status">Pick a topic first.</p>`; return; }
  area.innerHTML = `<p class="status">Generating questions…</p>`;
  try{
    const res = await fetch(`${API}/quiz/generate`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ topic: selectedTopic })
    });
    if(!res.ok) throw new Error(await res.text());
    const data = await res.json();
    quizState = { topic:selectedTopic, questions:data.questions, index:0, correct:0 };
    renderQuestion();
  }catch(err){
    area.innerHTML = `<p class="status">Couldn't generate the quiz. Try again.</p>`;
  }
});

function renderQuestion(){
  const area = document.getElementById("quizArea");
  if(quizState.index >= quizState.questions.length){
    recordQuizResult(quizState.topic, quizState.correct, quizState.questions.length);
    area.innerHTML = `<p class="status"><span style="font-family:var(--mono); font-weight:600; color:var(--ink);">${quizState.correct} / ${quizState.questions.length}</span> on ${escapeHtml(quizState.topic)}.</p>`;
    return;
  }
  const q = quizState.questions[quizState.index];
  const wrap = document.createElement("div");
  wrap.innerHTML = `<p class="progress">Question ${quizState.index+1} of ${quizState.questions.length}</p>`;
  const card = document.createElement("div");
  card.className = "q-card";
  card.innerHTML = `<h3>${escapeHtml(q.question)}</h3>` +
    q.options.map((opt,i)=>`<button class="opt" data-i="${i}">${escapeHtml(opt)}</button>`).join("") +
    `<div class="explain" style="display:none;"></div>`;
  wrap.appendChild(card);
  area.innerHTML = "";
  area.appendChild(wrap);
  card.querySelectorAll(".opt").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const i = Number(btn.dataset.i);
      card.querySelectorAll(".opt").forEach(b=>b.disabled=true);
      if(i === q.correctIndex){ btn.classList.add("correct"); quizState.correct++; }
      else{
        btn.classList.add("incorrect");
        card.querySelector(`.opt[data-i="${q.correctIndex}"]`).classList.add("correct");
      }
      const ex = card.querySelector(".explain");
      ex.style.display = "block";
      ex.textContent = q.explanation;
      const next = document.createElement("button");
      next.className = "primary"; next.style.marginTop = "12px"; next.textContent = "Next";
      next.addEventListener("click", ()=>{ quizState.index++; renderQuestion(); });
      card.appendChild(next);
    });
  });
}

async function recordQuizResult(topic, correct, total){
  try{
    await fetch(`${API}/quiz/record`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ topic, correct, total })
    });
  }catch(err){ console.error("Couldn't record quiz result", err); }
  renderWeakAreas();
}

async function renderWeakAreas(){
  const el = document.getElementById("weakAreas");
  try{
    const res = await fetch(`${API}/quiz/stats`);
    const rows = await res.json();
    if(!rows.length){ el.innerHTML = `<p class="status">No quizzes taken yet.</p>`; return; }
    rows.sort((a,b)=> (a.correct/a.total) - (b.correct/b.total));
    el.innerHTML = `<table class="weak"><thead><tr><th>Topic</th><th>Accuracy</th><th></th></tr></thead><tbody>` +
      rows.map(r=>{
        const pct = Math.round(100*r.correct/r.total);
        return `<tr><td>${escapeHtml(r.topic)}</td><td class="readout">${pct}% <span style="color:var(--muted); font-weight:400;">(${r.correct}/${r.total})</span></td>
          <td><div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div></td></tr>`;
      }).join("") + `</tbody></table>`;
  }catch(err){
    el.innerHTML = `<p class="status">Couldn't load stats.</p>`;
  }
}
renderWeakAreas();

/* ---------------- SQL Assistant ---------------- */
const dbStatus = document.getElementById("dbStatus");
const schemaInput = document.getElementById("schemaInput");

async function loadCurrentSchema(){
  try{
    const res = await fetch(`${API}/sql/schema`);
    const data = await res.json();
    schemaInput.value = data.schema;
    dbStatus.textContent = "Database ready.";
  }catch(err){
    dbStatus.textContent = "Couldn't reach the backend.";
  }
}
loadCurrentSchema();

document.getElementById("loadSchemaBtn").addEventListener("click", async ()=>{
  dbStatus.textContent = "Loading…";
  try{
    const res = await fetch(`${API}/sql/load`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ schema_sql: schemaInput.value })
    });
    if(!res.ok) throw new Error(await res.text());
    const data = await res.json();
    schemaInput.value = data.schema;
    dbStatus.textContent = "Database ready.";
  }catch(err){
    dbStatus.textContent = "That schema didn't run. Check the SQL and try again.";
  }
});

document.getElementById("reloadDefaultBtn").addEventListener("click", async ()=>{
  dbStatus.textContent = "Resetting…";
  try{
    const res = await fetch(`${API}/sql/reset`, { method:"POST" });
    const data = await res.json();
    schemaInput.value = data.schema;
    dbStatus.textContent = "Database ready.";
  }catch(err){
    dbStatus.textContent = "Couldn't reset.";
  }
});

document.getElementById("sqlForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const input = document.getElementById("sqlInput");
  const q = input.value.trim();
  const out = document.getElementById("sqlOut");
  if(!q) return;
  out.innerHTML = `<p class="status">Generating SQL…</p>`;
  try{
    const res = await fetch(`${API}/sql/ask`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ question: q })
    });
    if(!res.ok) throw new Error(await res.text());
    const data = await res.json();
    let html = `<code class="sql-out">${escapeHtml(data.sql)}</code><p class="hint" style="margin-bottom:0;">${escapeHtml(data.explanation||"")}</p>`;
    if(data.warning){
      html += `<div class="warn">${escapeHtml(data.warning)}</div>`;
    }else if(data.executed){
      if(!data.rows.length){
        html += `<p class="status">Ran successfully — no rows returned.</p>`;
      }else{
        html += `<table class="results"><thead><tr>${data.columns.map(c=>`<th>${escapeHtml(c)}</th>`).join("")}</tr></thead><tbody>` +
          data.rows.map(row=>`<tr>${row.map(v=>`<td>${v===null?"NULL":escapeHtml(String(v))}</td>`).join("")}</tr>`).join("") +
          `</tbody></table>`;
      }
    }
    out.innerHTML = html;
  }catch(err){
    out.innerHTML = `<p class="status">Couldn't generate a query just now. Try again.</p>`;
  }
});
