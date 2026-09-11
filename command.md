# 📡 Pluto+ SDR IP Radio & Mission Control UI Commands

Panduan lengkap menjalankan **FastAPI Backend (SDR Controller)** dan **Next.js Mission Control UI** di mesin lokal maupun remote (Raspberry Pi 5 / 2W / Linux Server).

---

## ⚡ Quick Start: 1-Script Runner (`./start_app.sh`)

Gunakan skrip `start_app.sh` untuk menjalankan backend dan UI sekaligus:

```bash
# Jalankan Backend + UI sekaligus
./start_app.sh all

# Jalankan di background (daemon mode)
./start_app.sh background

# Cek status layanan
./start_app.sh status

# Hentikan semua layanan
./start_app.sh stop
```

---

## 🌐 Menjalankan di Mesin Remote (Raspberry Pi / Linux)

### A. Melalui SSH Langsung dari Laptop (1 Command)

Ganti `raspi5.local` atau `raspi2w.local` dengan hostname/IP remote Anda:

```bash
# 1. Jalankan Backend & UI di background pada Remote:
ssh raspi5@raspi5.local "cd ~/sdr-fullduplex && ./start_app.sh background"

# 2. Cek status di Remote:
ssh raspi5@raspi5.local "cd ~/sdr-fullduplex && ./start_app.sh status"

# 3. Stop layanan di Remote:
ssh raspi5@raspi5.local "cd ~/sdr-fullduplex && ./start_app.sh stop"
```

---

### B. Menjalankan Manual di Sesi Remote (SSH Login)

Login ke remote terlebih dahulu:
```bash
ssh raspi5@raspi5.local
cd ~/sdr-fullduplex
```

#### 1. Jalankan Backend FastAPI Server
Driver Linux TUN (`radio0`) membutuhkan akses root (`sudo`):

```bash
# Mode Foreground (melihat log langsung di terminal):
sudo .venv/bin/python -m pluto_radio.cli server --host 0.0.0.0 --port 8000

# Mode Background (tetap berjalan setelah terminal ditutup):
sudo nohup .venv/bin/python -u -m pluto_radio.cli server --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

> **Akses Backend Remote**:
> - API Health: `http://<IP-REMOTE>:8000/health`
> - Swagger UI: `http://<IP-REMOTE>:8000/docs`

---

#### 2. Jalankan Next.js Mission Control UI
Masuk ke direktori `web-ui`:

```bash
cd ~/sdr-fullduplex/web-ui

# Install dependensi (hanya pertama kali):
npm install

# Mode Development (bind ke 0.0.0.0 agar bisa diakses dari LAN/WiFi):
npm run dev -- -H 0.0.0.0 -p 3000

# Mode Background (nohup):
nohup npm run dev -- -H 0.0.0.0 -p 3000 > ui.log 2>&1 &

# Atau Mode Production (lebih hemat RAM di Raspberry Pi):
npm run build
nohup npm run start -- -H 0.0.0.0 -p 3000 > ui.log 2>&1 &
```

> **Akses Frontend Remote**:
> Buka browser di laptop/HP: **`http://<IP-REMOTE>:3000`** (misal: `http://raspi5.local:3000` atau `http://192.168.1.50:3000`)

---

## 💻 Menjalankan di Mesin Lokal (macOS)

### 1. Terminal 1: Backend Server
```bash
cd /Users/mm/GitHub/sdr-fullduplex
source .venv/bin/activate
sudo .venv/bin/python -m pluto_radio.cli server --host 0.0.0.0 --port 8000
```

### 2. Terminal 2: Next.js Frontend Dashboard
```bash
cd /Users/mm/GitHub/sdr-fullduplex/web-ui
npm run dev -- -p 3001
```
Buka: **`http://localhost:3001`**

---

## 🔧 CLI Standalone Transceiver (Tanpa Web)

Jika ingin menjalankan radio link langsung dari terminal:

```bash
# Di Node 1 (Gateway 192.168.30.1):
sudo .venv/bin/python -m pluto_radio.cli link --tun --ip 192.168.30.1/24 --peer 192.168.30.3 --freq 2400000000

# Di Node 3 (Ground Mac 192.168.30.3):
sudo .venv/bin/python -m pluto_radio.cli link --tun --ip 192.168.30.3/24 --peer 192.168.30.1 --freq 2400000000 --uri usb:1.4.5
```

---

## 🧪 Testing & Unit Tests
```bash
cd MeshNetworkSDR
../.venv/bin/pytest tests/ -v
```
