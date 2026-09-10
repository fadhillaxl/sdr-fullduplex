# Pluto+ SDR IP Radio - Cross-Platform Command Cheat Sheet
### (macOS · Windows · Linux / Raspberry Pi)

Panduan lengkap instalasi, testing, deteksi hardware, dan operasional **Pluto+ SDR IP Radio** untuk **macOS**, **Windows**, dan **Linux**.

> 💡 **Panduan Lengkap Step-by-Step Ping via SDR**:
> * 🪟 **Windows PC ke Raspberry Pi**: [STEP_PING_WINDOWS_TO_PI.md](STEP_PING_WINDOWS_TO_PI.md) ([Web Interaktif](STEP_PING_WINDOWS_TO_PI.html))
> * 🍏 **macOS ke Raspberry Pi**: [STEP_PING_MAC_TO_PI.md](STEP_PING_MAC_TO_PI.md) ([Web Interaktif](STEP_PING_MAC_TO_PI.html))
> * 📡 **Live SDR Simulator Dashboard**: [preview.html](preview.html)

---

## 1. Instalasi & Virtual Environment

### 🍏 macOS (Terminal / Zsh / Bash)

```bash
# 1. Pindah ke direktori proyek
cd MeshNetworkSDR

# 2. Buat virtual environment
python3 -m venv .venv

# 3. Aktifkan virtual environment
source .venv/bin/activate

# 4. Install dependensi
pip install -r requirements.txt

# 5. Install paket pluto-radio (editable mode)
pip install -e .
```

---

### 🪟 Windows (PowerShell)

> **Catatan PowerShell**: Jika muncul pesan error execution policy, jalankan `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` terlebih dahulu di sesi PowerShell Anda.

```powershell
# 1. Pindah ke direktori proyek
cd MeshNetworkSDR

# 2. Buat virtual environment
python -m venv .venv

# 3. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install dependensi
pip install -r requirements.txt

# 5. Install paket pluto-radio (editable mode)
pip install -e .
```

---

### 🪟 Windows (Command Prompt - CMD)

```cmd
cd MeshNetworkSDR
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

---

### 🐧 Linux / Raspberry Pi

```bash
cd MeshNetworkSDR
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## 2. Testing & Validasi Unit Test (Pytest)

Test suite berjalan identik di semua platform (macOS, Windows, Linux):

```bash
# Menjalankan semua unit tests (20 tests)
pytest tests/ -v

# Menjalankan test modul spesifik
pytest tests/test_detection.py -v
pytest tests/test_config.py -v
pytest tests/test_cli.py -v
```

---

## 3. Deteksi Hardware Pluto SDR (Stage 0)

### 🍏 macOS & 🐧 Linux

```bash
# 1. Deteksi hardware otomatis (mencari USB atau IP default 192.168.2.1)
python scripts/detect_pluto.py

# 2. Deteksi dengan menentukan URI Pluto secara spesifik
python scripts/detect_pluto.py --uri ip:192.168.2.1

# 3. Mode Simulasi (menjalankan uji deteksi tanpa hardware Pluto fisik)
python scripts/detect_pluto.py --simulation

# 4. Melalui CLI Tool
pluto-radio status
pluto-radio status --simulation
pluto-radio stats
```

---

### 🪟 Windows (PowerShell / CMD)

```powershell
# 1. Deteksi hardware otomatis
python scripts\detect_pluto.py

# 2. Deteksi dengan URI spesifik
python scripts\detect_pluto.py --uri ip:192.168.2.1

# 3. Mode Simulasi
python scripts\detect_pluto.py --simulation

# 4. Melalui CLI Tool (pluto-radio.exe otomatis tersedia setelah pip install -e .)
pluto-radio status
pluto-radio status --simulation
pluto-radio stats
```

---

## 4. Entrypoint Scripts (Stage 1 Transmitter/Receiver)

### A. RF Transmitter (`scripts/tx.py`)

* **macOS / Linux**:
  ```bash
  python scripts/tx.py --simulation
  python scripts/tx.py --simulation --freq 433000000 --gain -20
  python scripts/tx.py --tone --freq 433000000 --gain -20
  ```
* **Windows**:
  ```powershell
  python scripts\tx.py --simulation
  python scripts\tx.py --simulation --freq 433000000 --gain -20
  python scripts\tx.py --tone --freq 433000000 --gain -20
  ```

### B. RF Receiver (`scripts/rx.py`)

* **macOS / Linux**:
  ```bash
  python scripts/rx.py --simulation
  python scripts/rx.py --freq 433000000
  ```
* **Windows**:
  ```powershell
  python scripts\rx.py --simulation
  python scripts\rx.py --freq 433000000
  ```

### C. Full Transceiver Link (`scripts/link.py`)

* **macOS / Linux**:
  ```bash
  python scripts/link.py --simulation
  python scripts/link.py
  ```
* **Windows**:
  ```powershell
  python scripts\link.py --simulation
  python scripts\link.py
  ```

---

## 5. Konfigurasi Driver & Jaringan Per Sistem Operasi

Pluto SDR menggunakan interface Ethernet-over-USB (RNDIS) dengan IP bawaan **`192.168.2.1`**. Agar host dapat berkomunikasi dengan Pluto, adapter jaringan di sisi komputer harus diatur pada subnet yang sama (misal `192.168.2.10`).

### 🍏 Pengaturan di macOS
1. Hubungkan Pluto SDR ke Mac menggunakan kabel data USB.
2. Buka **System Settings** -> **Network**.
3. Cari interface USB Ethernet Gadget baru (biasanya bernama *USB 10/100 LAN*).
4. Klik **Details...** -> tab **TCP/IP**:
   * **Configure IPv4**: *Manually*
   * **IP Address**: `192.168.2.10`
   * **Subnet Mask**: `255.255.255.0`
5. Test koneksi di Terminal:
   ```bash
   ping 192.168.2.1
   ```
6. (Opsional) Install libiio tools via Homebrew:
   ```bash
   brew install libiio
   iio_info -s
   ```

---

### 🪟 Pengaturan di Windows
1. Install [Analog Devices PlutoSDR Windows Driver (PlutoSDR-M2k-USB-Drivers.exe)](https://wiki.analog.com/university/tools/pluto/drivers/windows).
2. Tancapkan Pluto SDR ke port USB.
3. Buka **Control Panel** -> **Network and Internet** -> **Network Connections** (atau tekan `Win + R` lalu ketik `ncpa.cpl`).
4. Klik kanan adapter **PlutoSDR USB Ethernet/RNDIS Gadget** -> pilih **Properties**.
5. Klik ganda **Internet Protocol Version 4 (TCP/IPv4)**:
   * Pilih **Use the following IP address**:
   * **IP address**: `192.168.2.10`
   * **Subnet mask**: `255.255.255.0`
6. Test koneksi di PowerShell / CMD:
   ```powershell
   ping 192.168.2.1
   ```
7. (Opsional) Download & install [libiio Windows Installer](https://github.com/analogdevicesinc/libiio/releases) untuk mendapatkan utilitas `iio_info.exe`.

---

### 🐧 Pengaturan di Linux / Raspberry Pi
1. Salin udev rules PlutoSDR agar dapat diakses non-root:
   ```bash
   sudo wget -O /etc/udev/rules.d/53-adi-plutosdr-usb.rules https://raw.githubusercontent.com/analogdevicesinc/plutosdr-fw/master/scripts/53-adi-plutosdr-usb.rules
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
2. Tambahkan user ke group `plugdev` dan `dialout`:
   ```bash
   sudo usermod -a -G plugdev,dialout $USER
   ```
3. Konfigurasi interface `usb0` (jika tidak otomatis mendapat IP):
   ```bash
   sudo ifconfig usb0 192.168.2.10 netmask 255.255.255.0 up
   ping 192.168.2.1
   ```
