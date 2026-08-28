# Adaptive Path Planning for Indian Road Conditions — SIH Submission

Everything you need, in the order you need it. Five folders, numbered by
how they were built and how you'll actually use them.

```
01_matlab_reference/     — original algorithm validation (MATLAB). Reference only, don't run for SIH.
02_live_demo_browser/    — single HTML file, open directly in any browser. No setup.
03_driving_stack_python/ — Layer 1: the core pipeline, standalone + CLI testable.
04_backend_api/          — Layer 2: FastAPI + database, wraps Layer 1.
05_frontend_dashboard/   — Layer 3: React live dashboard, connects to Layer 2.
```

**For SIH, you run 04 + 05 together.** 01 is background proof-of-work, 02
is a zero-setup visual you can open anytime to explain the concept, 03 is
useful for quick CLI testing without spinning up the full web stack.

---

## Part 1 — Get this onto your Mac and into VS Code

1. Download the folder from this chat (or the zip, if that's what you
   got) and unzip it if needed — double-click the `.zip` in Finder.
2. Move the unzipped `SIH_ADAS_Complete` folder wherever you keep
   projects, e.g. `~/Projects/SIH_ADAS_Complete`.
3. Open **VS Code** → `File → Open Folder…` → select `SIH_ADAS_Complete`.
   You'll see all 5 numbered folders in the sidebar.
4. Install these VS Code extensions (Extensions icon in the left sidebar,
   or `Cmd+Shift+X`):
   - **Python** (by Microsoft) — for folders 03/04
   - **ES7+ React/Redux/JS snippets** and **ESLint** — for folder 05
5. Open the built-in terminal: `` Ctrl+` `` (backtick) or `Terminal → New Terminal`.
   You'll use this for everything below — no need to leave VS Code.

---

## Part 2 — Install prerequisites on your Mac

Open the VS Code terminal and check what you already have:

```bash
python3 --version     # need 3.10+
node --version          # need 18+
```

If either is missing, the easiest path is **Homebrew**:

```bash
# install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# then:
brew install python node
```

You'll also want **Docker Desktop** later for deployment — download it
from docker.com (Mac version, choose Apple Silicon or Intel depending on
your Mac).

---

## Part 3 — Run it locally, step by step

### Step 1: Sanity-check the core pipeline (folder 03)

Do this first — it's the fastest way to confirm your Python setup works
before touching the web stack.

```bash
cd 03_driving_stack_python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_all.py --scenario village_road --trials 2
```

You should see completion/collision output printed. If this works, your
Python environment is good.

### Step 2: Start the backend (folder 04)

Open a **new terminal tab** in VS Code (`Cmd+T` in the terminal panel, or
click the `+`) so folder 03's venv stays running separately.

```bash
cd 04_backend_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Leave this running. Open **http://localhost:8000/docs** in your browser —
you should see FastAPI's interactive API page. Try the `POST /api/runs`
endpoint right there with `{"scenario": "village_road", "seed": 42}` to
confirm the backend + database (SQLite file, created automatically) work.

### Step 3: Start the frontend (folder 05)

Another new terminal tab:

```bash
cd 05_frontend_dashboard
npm install
npm run dev
```

Open **http://localhost:5173**. Pick a scenario, click **Start live run**
— you should see it animate live, driven by the backend you started in
Step 2.

### If something breaks

Copy the exact error text and bring it back here — I'll debug it with
you directly. Common first-run issues:
- `port already in use` → something else is on 8000/5173; kill it
  (`lsof -i :8000` then `kill <PID>`) or change the port
- Frontend can't reach backend → make sure Step 2's terminal is still
  running and shows no errors
- `pip install` fails on a package → tell me the exact error, likely a
  Python version mismatch

---

## Part 4 — Deploy it (get a real public URL)

### Step A: Put it on GitHub

```bash
cd SIH_ADAS_Complete
git init
git add .
git commit -m "Initial SIH submission"
```
Create a new repo on github.com, then:
```bash
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

### Step B: Test the full Docker setup locally first

With Docker Desktop running:
```bash
cd 04_backend_api
docker compose up --build
```
This starts Postgres + the backend together. Confirm
`http://localhost:8000/docs` still works with this setup before deploying
— it proves the containerized version behaves the same as your local
venv version.

### Step C: Deploy the backend (Railway is the fastest path)

1. Go to railway.app, sign in with GitHub
2. **New Project → Deploy from GitHub repo** → pick your repo
3. Set the **root directory** to `04_backend_api` (Railway builds from
   your `Dockerfile` automatically)
4. **Add a Postgres database** from Railway's plugin marketplace — it
   auto-injects `DATABASE_URL` as an environment variable, which
   `database.py` already reads
5. Once deployed, Railway gives you a public URL like
   `https://your-app.up.railway.app` — that's your backend's live address

(Render.com works the same way if you prefer it — "New Web Service",
point at the repo, root directory `04_backend_api`, it detects the
Dockerfile.)

### Step D: Deploy the frontend

1. Go to vercel.com, sign in with GitHub
2. **New Project** → import your repo
3. Set **root directory** to `05_frontend_dashboard`
4. Under **Environment Variables**, add:
   - `VITE_API_BASE` = `https://your-app.up.railway.app`
   - `VITE_WS_BASE` = `wss://your-app.up.railway.app` (note: `wss://` not
     `ws://` for a deployed HTTPS backend)
5. Deploy — Vercel gives you a public URL like
   `https://your-app.vercel.app`

**That URL is what you hand to judges.** They open it, pick a scenario,
watch it run live — no setup on their end at all.

### Step E: Tighten CORS before final submission

In `04_backend_api/app/main.py`, find:
```python
allow_origins=["*"],
```
Change it to your actual Vercel URL:
```python
allow_origins=["https://your-app.vercel.app"],
```
Commit and push — Railway auto-redeploys.

---

## Part 5 — What's still genuinely left (not just deployment)

Deployment gets you a working link. These are the parts that make the
submission actually strong:

1. **Fix the market-area collision issue** — folder 03/04's
   `decision_logic.py` and `planner.py` need tuning; the dense-traffic
   scenario currently has a real ~33% collision rate in testing. Worth
   doing before judges see it.
2. **Technical report** — architecture, design choices, the 5-scenario
   metrics table, and this collision finding written up honestly as a
   "limitations" section (judges respect that more than a suspiciously
   perfect report).
3. **Demo video** — screen-record the deployed dashboard running all 5
   scenarios, 2-3 minutes, narrated.
4. Optional stretch: batch-run sweep button, replay mode, or the
   Raspberry Pi rover idea, if you want to go further.

---

## Quick reference — every command in one place

```bash
# Layer 1 sanity check
cd 03_driving_stack_python && source venv/bin/activate && python run_all.py

# Layer 2 (backend)
cd 04_backend_api && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Layer 3 (frontend)
cd 05_frontend_dashboard && npm run dev

# Full Docker stack
cd 04_backend_api && docker compose up --build
```
