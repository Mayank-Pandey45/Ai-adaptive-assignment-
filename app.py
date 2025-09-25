# app.py  -- Single-file Adaptive Assessment (backend + frontend + DB seed + analytics)
import os
import random
import time
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import inspect, text

DB_FILE = "data.db"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_FILE}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- Models ----------------
class Question(db.Model):
    __tablename__ = "question"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    options = db.Column(db.String, nullable=False)   # stringified list
    answer = db.Column(db.String, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)  # 1..5
    subject = db.Column(db.String, nullable=False)  # 'Maths','Physics','Chemistry','General'

class Session(db.Model):
    __tablename__ = "session"
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String, nullable=False)
    roll_no = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Response(db.Model):
    __tablename__ = "response"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    question_id = db.Column(db.Integer)
    correct = db.Column(db.Boolean)
    difficulty = db.Column(db.Integer)
    time_taken = db.Column(db.Float)  # seconds
    subject = db.Column(db.String)

# ---------------- Compatibility Check ----------------
def ensure_db_schema():
    """
    If DB exists but schema is older (missing subject), delete DB and recreate.
    This is a pragmatic choice for dev/hackathon. In production use migrations.
    """
    if not os.path.exists(DB_FILE):
        return  # will be created later

    # inspect columns in question table
    from sqlalchemy import create_engine
    engine = create_engine(f"sqlite:///{DB_FILE}")
    inspector = inspect(engine)
    if 'question' not in inspector.get_table_names():
        return
    cols = [c['name'] for c in inspector.get_columns('question')]
    # if subject column missing, recreate DB
    if 'subject' not in cols:
        print("-> Existing DB schema is old (missing 'subject'). Recreating DB (deleting data.db).")
        try:
            engine.dispose()
        except:
            pass
        os.remove(DB_FILE)
        return

# ---------------- Seed 70 Questions ----------------
def seed_questions():
    db.create_all()
    if Question.query.first():
        return

    subjects = ['Maths', 'Physics', 'Chemistry', 'General']
    Qs = []
    idx = 1

    # Difficulty distribution: 1 → very easy, 2 → easy-medium, 3 → medium, 4 → advanced, 5 → high-level
    distribution = [(1, 10), (2, 10), (3, 10), (4, 10), (5, 30)]

    for diff, count in distribution:
        for i in range(count):
            subj = random.choice(subjects)

            if subj == 'Maths':
                if diff == 1:
                    text = f"Maths Q{idx}: What is {i+1} + {i+2}?"
                    opts = [str(i+2), str(i+3), str(i+4), str(i+5)]
                    ans = str(i+3)
                elif diff == 2:
                    text = f"Maths Q{idx}: Multiply {i+2} * {i+3}"
                    opts = [str((i+2)*(i+3)), str((i+2)*(i+4)), str((i+3)*(i+3)), str((i+1)*(i+3))]
                    ans = str((i+2)*(i+3))
                elif diff == 3:
                    text = f"Maths Q{idx}: Solve for x: 2x + {i+1} = {i+5}"
                    opts = [str((i+5-(i+1))//2), str((i+5+i+1)//2), str(i), str(i+1)]
                    ans = str((i+5-(i+1))//2)
                elif diff == 4:
                    text = f"Maths Q{idx}: Derivative of x^{i+1}?"
                    opts = [f"{i+1}*x^{i}", f"{i}*x^{i-1}", f"x^{i+1}", f"1"]
                    ans = f"{i+1}*x^{i}"
                else:
                    text = f"Maths Q{idx}: High-level concept question about calculus."
                    opts = ["Proof/Explain", "Calculate", "Estimate", "None"]
                    ans = "Proof/Explain"

            elif subj == 'Physics':
                if diff <= 2:
                    text = f"Physics Q{idx}: SI unit of Force?"
                    opts = ["Newton","Joule","Pascal","Watt"]
                    ans = "Newton"
                elif diff == 3:
                    text = f"Physics Q{idx}: Speed of light (approx)?"
                    opts = ["3e8 m/s","3e6 m/s","3e5 km/s","9.8 m/s^2"]
                    ans = "3e8 m/s"
                elif diff == 4:
                    text = f"Physics Q{idx}: Newton's 2nd law formula?"
                    opts = ["F=ma","E=mc^2","P=mv","V=IR"]
                    ans = "F=ma"
                else:
                    text = f"Physics Q{idx}: Research-level question on quantum mechanics."
                    opts = ["Explain","Derive","Sketch","None"]
                    ans = "Derive"

            elif subj == 'Chemistry':
                if diff <= 2:
                    text = f"Chemistry Q{idx}: Water's chemical formula?"
                    opts = ["H2O","CO2","O2","H2"]
                    ans = "H2O"
                elif diff == 3:
                    text = f"Chemistry Q{idx}: Atomic number of Carbon?"
                    opts = ["6","12","8","14"]
                    ans = "6"
                elif diff == 4:
                    text = f"Chemistry Q{idx}: Boiling point of water?"
                    opts = ["100°C","90°C","80°C","120°C"]
                    ans = "100°C"
                else:
                    text = f"Chemistry Q{idx}: High-level question on chemical reactions."
                    opts = ["Explain","Calculate","Predict","None"]
                    ans = "Explain"

            else:  # General
                if diff <= 2:
                    text = f"General Q{idx}: Capital of France?"
                    opts = ["Paris","London","Berlin","Rome"]
                    ans = "Paris"
                elif diff == 3:
                    text = f"General Q{idx}: 5 + 7 * 2 = ?"
                    opts = ["19","24","26","17"]
                    ans = "19"
                elif diff == 4:
                    text = f"General Q{idx}: Largest ocean in the world?"
                    opts = ["Pacific","Atlantic","Indian","Arctic"]
                    ans = "Pacific"
                else:
                    text = f"General Q{idx}: High-level reasoning question."
                    opts = ["Explain","Estimate","Predict","None"]
                    ans = "Explain"

            Qs.append((text + f" [{subj}]", opts, ans, diff, subj))
            idx += 1

    # Insert all questions into DB
    for t, opts, ans, diff, subj in Qs:
        db.session.add(Question(text=t, options=str(opts), answer=str(ans), difficulty=diff, subject=subj))
    db.session.commit()
    print(f"Seeded {len(Qs)} questions into the database.")


# ---------------- API ----------------
@app.route('/_ping')
def ping(): 
    return jsonify({'ok': True})

@app.route('/start_session', methods=['POST'])
def start_session():
    data = request.json or {}
    student = data.get('student','Anonymous')
    roll_no = data.get('roll_no','-')
    s = Session(student=student, roll_no=roll_no)
    db.session.add(s)
    db.session.commit()
    return jsonify({'session_id': s.id, 'next_difficulty': 2})

@app.route('/next_question', methods=['POST'])
def next_question():
    data = request.json or {}
    target_diff = int(data.get('difficulty',3))
    session_id = data.get('session_id')
    used_q_ids = [r.question_id for r in Response.query.filter_by(session_id=session_id).all()] if session_id else []
    q = Question.query.filter(
        Question.difficulty.between(max(1,target_diff-1), min(5,target_diff+1))
    ).filter(~Question.id.in_(used_q_ids)).order_by(func.random()).first()
    if not q:
        q = Question.query.filter(~Question.id.in_(used_q_ids)).order_by(func.random()).first()
    if not q:
        q = Question.query.order_by(func.random()).first()
    return jsonify({'id': q.id, 'text': q.text, 'options': eval(q.options), 'difficulty': q.difficulty, 'subject': q.subject})

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json or {}
    session_id = data['session_id']
    qid = int(data['question_id'])
    selected = str(data.get('selected','')).strip()
    time_taken = float(data.get('time_taken', 0.0))
    q = Question.query.get(qid)
    correct = False
    if q and q.answer:
        try:
            correct = (selected.strip().lower() == str(q.answer).strip().lower())
        except Exception:
            correct = False
    r = Response(session_id=session_id, question_id=qid, correct=correct, difficulty=q.difficulty, time_taken=time_taken, subject=q.subject)
    db.session.add(r)
    db.session.commit()
    recent = Response.query.filter_by(session_id=session_id).order_by(Response.id.desc()).limit(7).all()
    acc = sum(1 for x in recent if x.correct)/len(recent) if recent else (1.0 if correct else 0.0)
    current = q.difficulty
    if acc >= 0.85:
        next_diff = min(5, current + 1)
    elif acc >= 0.6:
        next_diff = current
    else:
        next_diff = max(1, current - 1)
    return jsonify({'correct': correct, 'next_difficulty': next_diff})

@app.route('/teacher/analytics')
def teacher_analytics():
    sessions = Session.query.order_by(Session.created_at.desc()).all()
    out = []
    for s in sessions:
        res = Response.query.filter_by(session_id=s.id).all()
        attempts = len(res)
        if attempts == 0:
            avg_time = 0
            accuracy = 0
            avg_diff = 0
            focus = []
        else:
            avg_time = sum(r.time_taken for r in res)/attempts
            accuracy = sum(1 for r in res if r.correct)/attempts
            avg_diff = sum(r.difficulty for r in res)/attempts
            subj_stats = {}
            for r in res:
                subj_stats.setdefault(r.subject, {'total':0,'correct':0})
                subj_stats[r.subject]['total'] += 1
                if r.correct: subj_stats[r.subject]['correct'] += 1
            focus = []
            for subj, st in subj_stats.items():
                acc = st['correct']/st['total'] if st['total']>0 else 0
                if acc < 0.6:
                    focus.append({'subject': subj, 'accuracy': round(acc,2), 'attempts': st['total']})
        out.append({
            'session_id': s.id,
            'student': s.student,
            'roll_no': s.roll_no,
            'attempts': attempts,
            'avg_time': round(avg_time,2),
            'accuracy': round(accuracy,2),
            'avg_difficulty': round(avg_diff,2),
            'focus_areas': focus
        })
    return jsonify(out)

# ---------------- Frontend (single-page improved UI) ----------------
frontend_html = """(TRUNCATED FOR BREVITY: the full HTML/JS/CSS from prior message)"""

# NOTE: the actual frontend string is long. We'll include the full HTML below to keep file self-contained.
# Replace placeholder above with full HTML content (from previous combined UI) to use.
frontend_html = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Adaptive Assessment — Single File</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0f172a; --card:#0b1220; --muted:#94a3b8; --accent:#06b6d4; --success:#16a34a; --danger:#ef4444;
  }
  body{font-family:Inter,system-ui,Arial;background:linear-gradient(180deg,#071033,#081129);color:#e6eef8;margin:0;padding:24px;min-height:100vh;}
  .container{max-width:1100px;margin:0 auto;}
  header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}
  h1{margin:0;font-size:20px}
  .card{background:rgba(255,255,255,0.03);padding:18px;border-radius:12px;box-shadow:0 6px 18px rgba(2,6,23,0.6);margin-bottom:14px}
  .controls{display:flex;gap:10px;align-items:center}
  button{background:var(--accent);color:#04202b;border:none;padding:8px 12px;border-radius:8px;font-weight:600;cursor:pointer}
  button.ghost{background:transparent;border:1px solid rgba(255,255,255,0.06);color:var(--muted)}
  .grid{display:grid;grid-template-columns:1fr 360px;gap:14px}
  .question-box{min-height:220px}
  .q-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
  .difficulty{padding:6px 10px;border-radius:999px;background:rgba(255,255,255,0.04);font-weight:600}
  .options{display:flex;flex-direction:column;gap:8px}
  .opt{background:rgba(255,255,255,0.03);padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.02);cursor:pointer}
  .opt:hover{transform:translateY(-2px);transition:all .12s}
  .progress{height:10px;background:rgba(255,255,255,0.04);border-radius:999px;overflow:hidden;margin-top:12px}
  .progress > i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),#7c3aed);width:0%}
  .stat{font-size:12px;color:var(--muted)}
  .teacher-list{display:flex;flex-direction:column;gap:8px}
  table{width:100%;border-collapse:collapse;color:#d9eefc}
  th,td{padding:8px;border-bottom:1px solid rgba(255,255,255,0.03);text-align:left;font-size:13px}
  .small{font-size:12px;color:var(--muted)}
  input[type=text]{padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.05);background:transparent;color:inherit}
  .badge{padding:6px 8px;border-radius:8px;background:rgba(255,255,255,0.02);font-weight:700}
  .footer{margin-top:12px;color:var(--muted);font-size:13px}
  @media(max-width:920px){ .grid{grid-template-columns:1fr} .card{padding:12px} .controls{flex-direction:column;align-items:flex-start} }
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>Adaptive Assessment — Demo</h1>
      <div class="small">Personalized difficulty progression · Real-time teacher analytics</div>
    </div>
    <div class="controls">
      <button onclick="mode='student';render()">Student Mode</button>
      <button class="ghost" onclick="mode='teacher';render()">Teacher Mode</button>
    </div>
  </header>

  <div id="main"></div>

  <div class="footer">Tip: Start in Student Mode, fill name & roll, press <b>Start Test</b>. Each question times automatically. Teacher view shows per-student focus areas.</div>
</div>

<script>
let mode = 'student';
let session = null, question = null, diff = 2;
let qStart = null;
let qCount = 0;
const totalQuestionsForProgress = 20; // progress bar scale (we seeded 70 but progress just visual)

function fmt(n){ return Math.round(n*100)/100; }

async function render(){
  if(mode==='student') return renderStudent();
  return renderTeacher();
}

function studentFormHTML(){
  return `
  <div class="card">
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <div style="flex:1">
        <label class="small">Student Name</label><br>
        <input id="studentName" type="text" placeholder="Your name" />
      </div>
      <div style="width:160px">
        <label class="small">Roll No</label><br>
        <input id="rollNo" type="text" placeholder="e.g. 23CS101" />
      </div>
      <div>
        <label class="small">&nbsp;</label><br>
        <button onclick="startTest()">Start Test</button>
      </div>
      <div style="margin-left:auto" class="small">Difficulty: <span id="curDiff">2</span></div>
    </div>
  </div>
  `;
}

async function renderStudent(){
  let html = studentFormHTML();
  // question card
  html += `<div class="grid"><div class="card question-box">`;
  if(!session){
    html += `<div style="padding:20px"><h2>Ready to start?</h2><p class="stat">Enter your name and roll no, then press Start Test. Questions adapt based on your performance.</p></div>`;
  } else {
    if(question){
      html += `<div class="q-meta"><div><span class="badge">Q ${qCount+1}</span> &nbsp; <span class="small">Subject: ${question.subject}</span></div><div class="difficulty">Difficulty ${question.difficulty}</div></div>`;
      html += `<h3 style="margin-top:6px">${question.text}</h3>`;
      html += `<div class="options">`;
      for(const o of question.options){
        html += `<div class="opt" onclick="chooseOption('${escapeJs(o)}')">${o}</div>`;
      }
      html += `</div>`;
      html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px"><div class="stat">Time: <span id="timer">0s</span></div><div style="min-width:240px"><div class="progress"><i id="prog" style="width:0%"></i></div></div></div>`;
    } else {
      html += `<div style="padding:20px"><h3>Loading next question...</h3></div>`;
    }
  }
  html += `</div>`;

  // right column: stats
  html += `<div class="card" style="height:100%"><h3>Session</h3>`;
  if(!session){
    html += `<div class="small">No active session</div>`;
  } else {
    html += `<div class="small"><b>Student:</b> ${escapeHtml(session.student)}<br><b>Roll:</b> ${escapeHtml(session.roll_no)}</div>`;
    html += `<hr style="margin:10px 0">`;
    html += `<div class="small"><b>Questions Attempted:</b> <span id="attempted">0</span></div>`;
    html += `<div class="small"><b>Avg time / Q:</b> <span id="avgtime">0</span>s</div>`;
    html += `<div class="small"><b>Accuracy:</b> <span id="acc">0</span></div>`;
    html += `<div style="margin-top:10px"><button onclick="endSession()" class="ghost">End Session</button></div>`;
  }
  html += `</div></div>`;

  document.getElementById('main').innerHTML = html;
  if(session && question){ startTimer(); updateSessionStatsUI(); }
}

function escapeHtml(s){ return String(s||'').replace(/[&<>"']/g, (m)=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function escapeJs(s){ return String(s||'').replace(/'/g,"\\'").replace(/\\n/g,' '); }

let timerInterval = null;
let elapsed = 0;
function startTimer(){
  elapsed = 0;
  qStart = Date.now();
  if(timerInterval) clearInterval(timerInterval);
  document.getElementById('timer').innerText = '0s';
  timerInterval = setInterval(()=>{
    elapsed = (Date.now()-qStart)/1000;
    document.getElementById('timer').innerText = Math.round(elapsed)+'s';
    // progress  (cap at 60s)
    let pct = Math.min(100, (elapsed/30)*100);
    document.getElementById('prog').style.width = pct+'%';
  },200);
}

function stopTimer(){
  if(timerInterval) clearInterval(timerInterval);
  timerInterval = null;
  return (Date.now()-qStart)/1000;
}

async function startTest(){
  const name = document.getElementById('studentName').value.trim() || 'Anonymous';
  const roll = document.getElementById('rollNo').value.trim() || '-';
  const res = await fetch('/start_session', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({student:name, roll_no:roll})});
  const data = await res.json();
  session = {session_id:data.session_id, student:name, roll_no:roll};
  diff = data.next_difficulty || 2;
  qCount = 0;
  await loadNext();
  render();
}

async function loadNext(){
  // fetch next question for current difficulty
  document.getElementById('curDiff') && (document.getElementById('curDiff').innerText = diff);
  const res = await fetch('/next_question', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:session.session_id, difficulty:diff})});
  question = await res.json();
  qCount += 1;
}

async function chooseOption(opt){
  const t = stopTimer();
  const chosen = opt;
  const res = await fetch('/submit_answer', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
    session_id: session.session_id,
    question_id: question.id,
    selected: chosen,
    time_taken: Math.round(t*100)/100
  })});
  const r = await res.json();
  diff = r.next_difficulty || diff;
  await updateSessionStats();
  await loadNext();
  render();
}

async function updateSessionStats(){
  const res = await fetch('/teacher/analytics');
  const data = await res.json();
  const me = data.find(d=>d.session_id===session.session_id);
  if(me){
    session.stats = me;
  }
}

function updateSessionStatsUI(){
  if(!session || !session.stats) return;
  document.getElementById('attempted').innerText = session.stats.attempts;
  document.getElementById('avgtime').innerText = session.stats.avg_time;
  document.getElementById('acc').innerText = session.stats.accuracy;
}

async function endSession(){
  alert('Session ended. You can switch to Teacher Mode to see detailed analytics.');
  session = null;
  question = null;
  diff = 2;
  render();
}

async function renderTeacher(){
  const res = await fetch('/teacher/analytics');
  const data = await res.json();
  let html = `<div class="card"><h2>Teacher Dashboard</h2><div class="small">Overview of student sessions</div></div>`;
  html += `<div class="card"><table><thead><tr><th>Student</th><th>Roll</th><th>Attempts</th><th>Avg Time (s)</th><th>Accuracy</th><th>Avg Diff</th><th>Focus Areas</th></tr></thead><tbody>`;
  for(const s of data){
    let focus = '-';
    if(s.focus_areas && s.focus_areas.length){
      focus = s.focus_areas.map(f=>`${f.subject} (${Math.round(f.accuracy*100)}%)`).join('<br>');
    }
    html += `<tr><td>${escapeHtml(s.student)}</td><td>${escapeHtml(s.roll_no)}</td><td>${s.attempts}</td><td>${s.avg_time}</td><td>${Math.round(s.accuracy*100)}%</td><td>${s.avg_difficulty}</td><td>${focus}</td></tr>`;
  }
  html += `</tbody></table></div>`;
  html += `<div class="card"><h3>Notes</h3><div class="small">Focus Areas are subjects where student accuracy < 60%. Use this to plan targeted practice modules.</div></div>`;
  document.getElementById('main').innerHTML = html;
}

(async function init(){
  try { await fetch('/_ping'); } catch(e){}
  render();
})();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(frontend_html)

# ---------------- Startup ----------------
if __name__ == '__main__':
    # If DB exists and is incompatible, recreate it (dev friendly)
    ensure_db_schema()
    with app.app_context():
        db.create_all()
        seed_questions()
    app.run(debug=True)
