# PillGuard — Windows Setup Guide

Smart pill dispenser with Raspberry Pi sensor/camera, FastAPI backend, and React dashboard. This guide walks through running the backend and frontend on a Windows laptop, with the Pi optionally connected over WiFi for hardware monitoring.

---

## Prerequisites

Install these on your Windows machine first:

1. **Python 3.11+** — https://www.python.org/downloads/windows/
   - During install, check **"Add Python to PATH"**
2. **Node.js 20+** — https://nodejs.org/en/download
3. **Git** — https://git-scm.com/download/win
4. **OpenSSH Client** (for connecting to the Pi) — already included in Windows 10/11. If not, install via:
   `Settings → Apps → Optional features → Add → OpenSSH Client`

Verify installs by opening **PowerShell** and running:
```powershell
python --version
node --version
git --version
ssh -V
```

---

## 1. Clone the project

Open PowerShell and run:
```powershell
cd $HOME\Desktop
git clone <your-repo-url> PillGuard
cd PillGuard
```

Or copy the `PillGuard` folder to `C:\Users\<you>\Desktop\PillGuard`.

---

## 2. Create the `.env` file

In the project root (`PillGuard\`), create a file called `.env` with this content:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
CARETAKER_PHONE=+1xxxxxxxxxx
BACKEND_URL=http://localhost:8000
```

Fill in your real keys. You can leave Twilio blank if you don't want SMS — the backend will still log events and the dashboard will still work.

---

## 3. Backend setup (Python)

In PowerShell, from the `PillGuard` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn twilio apscheduler python-dotenv anthropic requests
```

If PowerShell blocks the activate script, run this first (as admin):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then run the backend:
```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The backend should be running at `http://localhost:8000`. You'll see startup logs and "Application startup complete."

Test it in a browser: `http://localhost:8000/patient/1` → should return the default patient JSON.

---

## 4. Frontend setup (React)

Open a **second PowerShell window**, then:

```powershell
cd $HOME\Desktop\PillGuard\frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser — you should see the PillGuard dashboard.

---

## 5. Simulation mode (no hardware needed)

To test the Claude Vision + backend flow without a physical Pi, open a **third PowerShell window**:

```powershell
cd $HOME\Desktop\PillGuard
.\.venv\Scripts\Activate.ps1
python -m pi.pi_main --simulate --test-image path\to\any\photo.jpg
```

Press ENTER to simulate opening the pill box. The app will:
1. "Capture" frames (using your test image)
2. Send them to Claude Vision API
3. Classify as TOOK_PILL / NO_TAKE / DISTRESS / NO_SHOW
4. Post the result to the backend
5. Show it on the dashboard

---

## 6. Connecting a physical Raspberry Pi

If you have a Pi wired up (sensor, LEDs, buzzer, LCD, webcam):

### Find your Windows laptop's IP
```powershell
ipconfig
```
Look for **IPv4 Address** under your active WiFi adapter (e.g. `192.168.1.42`).

### Find the Pi's IP
From the Pi directly (keyboard + monitor) or via your router's admin page. Then SSH from Windows:
```powershell
ssh pi@<pi-ip-address>
```

### On the Pi, set up the project
```bash
mkdir -p ~/pillguard
cd ~/pillguard
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
sudo apt update && sudo apt install -y python3-pip python3-opencv
pip install anthropic RPi.GPIO RPLCD requests python-dotenv smbus2
```

### Copy project files from Windows to Pi
From PowerShell on your Windows laptop:
```powershell
scp -r .\pi pi@<pi-ip>:~/pillguard/
scp .\.env pi@<pi-ip>:~/pillguard/
```

### Edit `.env` on the Pi
SSH into the Pi and change `BACKEND_URL` to point at your Windows laptop:
```bash
nano ~/pillguard/.env
```
Change:
```
BACKEND_URL=http://<windows-laptop-ip>:8000
```
Save with `Ctrl+O`, Enter, `Ctrl+X`.

### Allow the Pi through Windows Firewall
On your Windows laptop, you may need to allow inbound connections on port 8000:
1. Open **Windows Defender Firewall with Advanced Security**
2. **Inbound Rules → New Rule → Port → TCP → 8000 → Allow**
3. Apply to Private networks only (if you're on trusted WiFi)

### Run the Pi controller
```bash
cd ~/pillguard
source .venv/bin/activate
python -m pi.pi_main
```

Now when you open the pill box lid, the Pi's HC-SR04 will trigger, the webcam captures 18 frames, Claude classifies them, and the result appears on your dashboard at `http://localhost:5173`.

---

## Hardware wiring (for reference)

| Component | GPIO Pin |
|-----------|----------|
| HC-SR04 TRIG | 23 |
| HC-SR04 ECHO | 24 (through a 1kΩ + 2kΩ voltage divider) |
| Green LED | 17 (through 220Ω resistor) |
| Red LED | 27 (through 220Ω resistor) |
| Buzzer | 22 |
| LCD SDA | 2 |
| LCD SCL | 3 |

Enable I2C on the Pi first (for the LCD):
```bash
sudo raspi-config
```
Navigate: **Interface Options → I2C → Yes → Finish**, then reboot.

---

## Troubleshooting

**"Address already in use" (port 8000):**
```powershell
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

**Backend POST fails from Pi:**
- Verify `BACKEND_URL` in the Pi's `.env` points at your Windows laptop's IP, not `localhost`
- Make sure Windows Firewall allows inbound on port 8000
- Test from the Pi: `curl http://<windows-ip>:8000/patient/1`

**Claude Vision errors:**
- Check your `ANTHROPIC_API_KEY` is valid and has credits
- Check the Pi's venv has `anthropic` installed: `pip list | grep anthropic`

**Frontend shows "No data yet":**
- Make sure the backend is running
- Check browser devtools → Network tab for failed `/api/*` requests

**PowerShell "cannot run scripts" error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Project structure

```
PillGuard/
├── backend/          FastAPI server + SQLite + scheduler
├── frontend/         React dashboard (Vite + Tailwind + Recharts)
├── pi/               Pi controller (sensor + camera + Claude)
├── .env              Secrets (create this yourself)
└── README_WINDOWS.md
```
