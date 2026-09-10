# Pluto SDR Full-Duplex (Legacy)
python full-duplex.py --role A --tx-gain -20 --rx-gain 10

python full-duplex.py --role B --tx-gain -20 --rx-gain 10

python full-duplex.py --role A --tx-gain 0 --rx-gain 45

python full-duplex.py --role B --tx-gain 0 --rx-gain 45

---

# Pluto+ SDR Short-Range IP Radio (MeshNetworkSDR)

Untuk dokumentasi lengkap, lihat [MeshNetworkSDR/command.md](MeshNetworkSDR/command.md).

### 1. Test & Validasi
```bash
cd MeshNetworkSDR
../.venv/bin/pytest tests/ -v
```

### 2. Deteksi Pluto SDR (Hardware & Simulation)
```bash
# Mode Hardware
../.venv/bin/python scripts/detect_pluto.py

# Mode Simulasi (tanpa Pluto fisik)
../.venv/bin/python scripts/detect_pluto.py --simulation

# Menggunakan CLI tool
../.venv/bin/pluto-radio status --simulation
../.venv/bin/pluto-radio stats
```

### 3. Transceiver Entrypoints (Stage 1)
```bash
../.venv/bin/python scripts/tx.py --simulation
../.venv/bin/python scripts/rx.py --simulation
../.venv/bin/python scripts/link.py --simulation
```

### 4. Windows (PowerShell)
```powershell
cd MeshNetworkSDR
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
python scripts\detect_pluto.py --simulation
pluto-radio status --simulation
```


