"""Passive Automatic Antenna Type Classifier for ADALM-Pluto / Pluto+ SDR.

Performs multi-band RF frequency sweeps (433 MHz, 900 MHz, 2.44 GHz, 5.8 GHz)
measuring ambient spectral power (RSSI) and Signal-to-Noise Ratio (SNR) to classify
the connected antenna type.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import adi
    HAS_ADI = True
except ImportError:
    HAS_ADI = False

from ..dsp.rf_metrics import compute_rf_metrics

logger = logging.getLogger(__name__)

# Test Frequency Points representing distinct RF spectrum allocations
TEST_FREQUENCIES: list[dict[str, Any]] = [
    {
        "freq_hz": 433_000_000,
        "label": "433 MHz",
        "band": "VHF/UHF ISM",
        "description": "Sub-GHz ISM Band / Ham Radio",
    },
    {
        "freq_hz": 900_000_000,
        "label": "900 MHz",
        "band": "Cellular Low-Band",
        "description": "GSM / LTE Band 8 / LoRa 915",
    },
    {
        "freq_hz": 2_440_000_000,
        "label": "2440 MHz",
        "band": "Wi-Fi 2.4 GHz",
        "description": "2.4 GHz ISM / Wi-Fi / Bluetooth",
    },
    {
        "freq_hz": 5_800_000_000,
        "label": "5800 MHz",
        "band": "Wi-Fi 5.8 GHz",
        "description": "5.8 GHz ISM / Wi-Fi 5/6 / UNII-3",
    },
]


@dataclass
class AntennaScanPoint:
    """Individual frequency measurement result."""
    freq_hz: int
    freq_label: str
    band_name: str
    rssi_dbfs: float
    snr_db: float
    noise_floor_dbfs: float


@dataclass
class AntennaClassification:
    """Final decision output from antenna frequency sweep."""
    result_text: str
    antenna_type: str
    confidence_pct: float
    summary: str
    recommendation: str
    measurements: list[AntennaScanPoint]
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_text": self.result_text,
            "antenna_type": self.antenna_type,
            "confidence_pct": self.confidence_pct,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "measurements": [asdict(m) for m in self.measurements],
            "timestamp": self.timestamp,
        }


def classify_antenna_from_measurements(
    measurements: list[AntennaScanPoint],
) -> Tuple[str, str, float, str, str]:
    """Execute decision logic based on RSSI and SNR spectral profile across 4 bands.

    Returns:
        Tuple of (result_text, antenna_type, confidence_pct, summary, recommendation)
    """
    if len(measurements) != 4:
        return (
            "Status: Pengukuran Tidak Lengkap",
            "unknown",
            0.0,
            "Frekuensi uji kurang dari 4 titik.",
            "Ulangi proses sweep antena.",
        )

    # Map measurements by frequency
    m_map = {m.freq_hz: m for m in measurements}
    rssi_433 = m_map[433_000_000].rssi_dbfs
    rssi_900 = m_map[900_000_000].rssi_dbfs
    rssi_2440 = m_map[2_440_000_000].rssi_dbfs
    rssi_5800 = m_map[5_800_000_000].rssi_dbfs

    all_rssi = [rssi_433, rssi_900, rssi_2440, rssi_5800]
    max_rssi = max(all_rssi)
    min_rssi = min(all_rssi)
    avg_rssi = sum(all_rssi) / 4.0
    spread = max_rssi - min_rssi

    # Rule 1: Sinyal drop di seluruh band (< -70 dBFS)
    # Menandakan tidak ada resonansi antena, konektor terbuka, atau kabel putus
    if all(r < -70.0 for r in all_rssi):
        return (
            "PERINGATAN: Antena Tidak Terdeteksi / Putus!",
            "disconnected",
            95.0,
            "Level sinyal di bawah -70 dBFS pada semua pita frekuensi.",
            "Periksa konektor SMA pada port RX/TX Pluto+ dan pastikan antena terpasang kuat.",
        )

    # Rule 2: RSSI stabil kuat (> -45 dBFS) di SEMUA frekuensi uji
    # Menandakan antena wideband broadband (Log-Periodic / Vivaldi / UWB Discone)
    if all(r > -45.0 for r in all_rssi) and spread <= 18.0:
        return (
            "Antena Terdeteksi: Ultra-Wideband (UWB) / Log-Periodic",
            "uwb",
            92.0,
            f"Respon frekuensi sangat rata dari 433 MHz hingga 5.8 GHz (rata-rata {avg_rssi:.1f} dBFS, spread {spread:.1f} dB).",
            "Cocok untuk full-duplex frequency hopping dan multi-band scanning 70 MHz - 6 GHz.",
        )

    # Rule 3: RSSI kuat di 900 MHz dan 2440 MHz (> -42 dBFS), drop di 433 & 5800
    # Menandakan antena multiband seluler (misal GSM 900 / DCS / LTE / Wi-Fi whip)
    if (rssi_900 > -42.0 and rssi_2440 > -42.0) and (rssi_900 > rssi_433 + 8.0 and rssi_2440 > rssi_5800 + 8.0):
        return (
            "Antena Terdeteksi: LTE / Cellular Multiband",
            "lte_multiband",
            88.0,
            f"Resonansi ganda terdeteksi di 900 MHz ({rssi_900:.1f} dBFS) dan 2440 MHz ({rssi_2440:.1f} dBFS).",
            "Optimal untuk link komunikasi seluler pita menengah dan Wi-Fi 2.4 GHz.",
        )

    # Rule 4: RSSI hanya kuat (> -40 dBFS) di 2440 MHz dan drop di tempat lain
    # Antena monoband Wi-Fi 2.4 GHz / Bluetooth ISM
    if rssi_2440 > -40.0 and (rssi_2440 - max(rssi_433, rssi_900, rssi_5800) >= 10.0):
        return (
            "Antena Terdeteksi: Wi-Fi 2.4 GHz",
            "wifi_24",
            94.0,
            f"Resonansi tajam pada 2440 MHz ({rssi_2440:.1f} dBFS) dengan atenuasi tinggi di luar pita.",
            "Sangat ideal untuk link Stage 7 Pluto SDR mesh pada 2400 MHz.",
        )

    # Rule 5: RSSI hanya kuat di 433 MHz (> -40 dBFS) dan drop di tempat lain
    # Antena monoband VHF/UHF Sub-GHz
    if rssi_433 > -40.0 and (rssi_433 - max(rssi_900, rssi_2440, rssi_5800) >= 10.0):
        return (
            "Antena Terdeteksi: VHF/UHF (433 MHz)",
            "vhf_uhf",
            92.0,
            f"Resonansi dominan di 433 MHz ({rssi_433:.1f} dBFS), tidak cocok untuk frekuensi GHz.",
            "Gunakan frekuensi carrier 433 MHz untuk efisiensi propagasi terbaik.",
        )

    # Rule 6: RSSI kuat di 5800 MHz saja (> -40 dBFS)
    # Antena Wi-Fi 5.8 GHz / High Band FPV
    if rssi_5800 > -40.0 and (rssi_5800 - max(rssi_433, rssi_900, rssi_2440) >= 10.0):
        return (
            "Antena Terdeteksi: Wi-Fi 5.8 GHz / High Band",
            "wifi_58",
            90.0,
            f"Resonansi terpusat pada pita 5.8 GHz ({rssi_5800:.1f} dBFS).",
            "Gunakan untuk link point-to-point bandwidth tinggi di 5.8 GHz.",
        )

    # Heuristic Relative Peak Matching (apabila level daya noise lingkungan lebih rendah):
    if max_rssi == rssi_2440 and (rssi_2440 - max(rssi_433, rssi_900, rssi_5800) >= 7.0):
        return (
            "Antena Terdeteksi: Wi-Fi 2.4 GHz",
            "wifi_24",
            82.0,
            f"Karakteristik dominan puncak pada 2440 MHz ({rssi_2440:.1f} dBFS).",
            "Direkomendasikan untuk jaringan SDR 2.4 GHz.",
        )

    if max_rssi == rssi_433 and (rssi_433 - max(rssi_900, rssi_2440, rssi_5800) >= 7.0):
        return (
            "Antena Terdeteksi: VHF/UHF (433 MHz)",
            "vhf_uhf",
            80.0,
            f"Karakteristik puncak pada 433 MHz ({rssi_433:.1f} dBFS).",
            "Cocok untuk pita Sub-GHz ISM.",
        )

    if max_rssi == rssi_5800 and (rssi_5800 - max(rssi_433, rssi_900, rssi_2440) >= 7.0):
        return (
            "Antena Terdeteksi: Wi-Fi 5.8 GHz / High Band",
            "wifi_58",
            80.0,
            f"Puncak respon spektrum pada 5.8 GHz ({rssi_5800:.1f} dBFS).",
            "Gunakan pita frekuensi 5.8 GHz.",
        )

    if (rssi_900 > rssi_433 + 5.0 and rssi_2440 > rssi_5800 + 5.0):
        return (
            "Antena Terdeteksi: LTE / Cellular Multiband",
            "lte_multiband",
            75.0,
            f"Respon terkuat di 900 MHz ({rssi_900:.1f} dBFS) dan 2440 MHz ({rssi_2440:.1f} dBFS).",
            "Mendukung operasi multiband.",
        )

    return (
        "Antena Terdeteksi: Antena Umum / Respon Campuran",
        "general",
        65.0,
        f"Level sinyal rata-rata {avg_rssi:.1f} dBFS tanpa resonansi tunggal yang dominan.",
        "Dapat digunakan untuk operasi SDR multi-kanal.",
    )


def scan_dan_deteksi_antena_pluto(
    sdr: Any = None,
    uri: Optional[str] = None,
    simulation: bool = False,
    gain_db: int = 60,
    rf_bandwidth: int = 5_000_000,
    num_samples: int = 16384,
    simulated_profile: Optional[str] = None,
) -> AntennaClassification:
    """Fungsi utama deteksi otomatis tipe antena SDR Pluto+.
    
    Melakukan frequency sweep pasif pada 4 titik uji (433M, 900M, 2440M, 5800M),
    mengukur ambient RSSI & SNR, serta mengklasifikasi tipe antena secara software.
    
    Args:
        sdr: Instance adi.Pluto aktif, atau None untuk inisialisasi otomatis.
        uri: Target Pluto URI (misal 'ip:pluto.local' atau 'ip:192.168.2.1').
        simulation: Jalankan dalam mode simulasi perangkat lunak.
        gain_db: Fixed hardware gain dB (default 60 dB untuk perbandingan adil).
        rf_bandwidth: Bandwidth filter analog RX AD9361 dalam Hz.
        num_samples: Jumlah sampel IQ yang diambil di setiap titik frekuensi.
        simulated_profile: Profil antena uji untuk simulasi ('wifi_24', 'vhf_uhf', 'lte_multiband', 'wifi_58', 'uwb', 'disconnected').

    Returns:
        AntennaClassification berisi hasil klasifikasi, rekomendasi, dan data sweep.
    """
    logger.info("Memulai Passive Antenna Sweep pada Pluto+ SDR...")

    # Mode Simulasi (Unit Testing atau Tanpa Hardware SDR Fisik)
    if simulation or (not HAS_ADI and sdr is None):
        logger.info("Menjalankan deteksi antena dalam Mode Simulasi.")
        measurements: list[AntennaScanPoint] = []
        profile = simulated_profile or "wifi_24"

        # Tentukan baseline RSSI simulasi berdasarkan profil
        profile_rssi_map = {
            "wifi_24": {433_000_000: -74.5, 900_000_000: -71.2, 2_440_000_000: -36.4, 5_800_000_000: -78.1},
            "vhf_uhf": {433_000_000: -35.2, 900_000_000: -73.1, 2_440_000_000: -76.8, 5_800_000_000: -79.4},
            "lte_multiband": {433_000_000: -72.0, 900_000_000: -38.5, 2_440_000_000: -39.1, 5_800_000_000: -76.0},
            "wifi_58": {433_000_000: -78.0, 900_000_000: -76.4, 2_440_000_000: -72.1, 5_800_000_000: -34.8},
            "uwb": {433_000_000: -41.2, 900_000_000: -40.8, 2_440_000_000: -42.1, 5_800_000_000: -43.5},
            "disconnected": {433_000_000: -82.1, 900_000_000: -81.4, 2_440_000_000: -83.7, 5_800_000_000: -85.2},
        }
        chosen_profile = profile_rssi_map.get(profile, profile_rssi_map["wifi_24"])

        for pt in TEST_FREQUENCIES:
            f_hz = pt["freq_hz"]
            base_rssi = chosen_profile[f_hz]
            noise_floor = -85.0
            snr = max(0.0, base_rssi - noise_floor)
            measurements.append(
                AntennaScanPoint(
                    freq_hz=f_hz,
                    freq_label=pt["label"],
                    band_name=pt["band"],
                    rssi_dbfs=round(base_rssi, 1),
                    snr_db=round(snr, 1),
                    noise_floor_dbfs=noise_floor,
                )
            )

        res_text, ant_type, conf, summary, rec = classify_antenna_from_measurements(measurements)
        return AntennaClassification(
            result_text=res_text,
            antenna_type=ant_type,
            confidence_pct=conf,
            summary=summary,
            recommendation=rec,
            measurements=measurements,
            timestamp=time.time(),
        )

    # Inisialisasi Hardware SDR ADALM-Pluto jika belum di-passing
    sdr_instance = sdr
    owns_sdr = False

    if sdr_instance is None:
        from .pluto import find_candidate_uris
        target_uri = uri
        candidates = find_candidate_uris(target_uri)
        for cand in candidates:
            try:
                sdr_instance = adi.Pluto(uri=cand)
                owns_sdr = True
                break
            except Exception as e:
                logger.debug("Probing candidate %s gagal: %s", cand, e)

    if sdr_instance is None:
        raise RuntimeError("Tidak dapat terhubung ke ADALM-Pluto SDR untuk deteksi antena.")

    # 1. Simpan State Asli Perangkat untuk Restorasi Pasca-Scan
    orig_rx_lo = getattr(sdr_instance, "rx_lo", 2_400_000_000)
    orig_bw = getattr(sdr_instance, "rx_rf_bandwidth", 2_000_000)
    orig_gain_mode = getattr(sdr_instance, "gain_control_mode_chan0", "slow_attack")
    orig_gain = getattr(sdr_instance, "rx_hardwaregain_chan0", 56)

    measurements = []

    try:
        # 2. Konfigurasi Gain Manual Tetap (Fixed Gain)
        # Menghindari distorsi pengukuran akibat AGC otomatis menyesuaikan gain di setiap frekuensi
        sdr_instance.gain_control_mode_chan0 = "manual"
        sdr_instance.rx_hardwaregain_chan0 = int(gain_db)
        sdr_instance.rx_rf_bandwidth = int(rf_bandwidth)
        sdr_instance.rx_buffer_size = int(num_samples)

        # 3. Frequency Sweep Melintasi 4 Titik Uji
        for pt in TEST_FREQUENCIES:
            target_freq = pt["freq_hz"]
            logger.info("Tuning LO ke %s (%d Hz)...", pt["label"], target_freq)

            # A. Ganti Frekuensi Local Oscillator (LO)
            sdr_instance.rx_lo = int(target_freq)

            # B. Waktu Stabilisasi PLL (Synthesizer Settling Time)
            # AD9361 membutuhkan ~15-25 ms agar fractional-N PLL terkunci stabil
            time.sleep(0.025)

            # C. Buang Buffer Pertama (Flush DMA Pipeline)
            # Menghapus sampel sisa frekuensi sebelumnya dari kernel ring buffer
            try:
                _ = sdr_instance.rx()
            except Exception:
                pass

            # D. Akuisisi Sampel IQ Sebenarnya
            samples = sdr_instance.rx()
            samples_c64 = np.asarray(samples, dtype=np.complex64)

            # E. Hitung Metrik Spektral (RSSI & SNR)
            metrics = compute_rf_metrics(samples_c64, sample_rate=getattr(sdr_instance, "sample_rate", 2000000))

            measurements.append(
                AntennaScanPoint(
                    freq_hz=target_freq,
                    freq_label=pt["label"],
                    band_name=pt["band"],
                    rssi_dbfs=round(metrics.rssi_dbfs, 1),
                    snr_db=round(metrics.snr_db, 1),
                    noise_floor_dbfs=round(metrics.noise_dbfs, 1),
                )
            )

    finally:
        # 4. Restorasi Aman Konfigurasi Frekuensi & Gain Asli Pluto+
        try:
            sdr_instance.rx_lo = int(orig_rx_lo)
            sdr_instance.rx_rf_bandwidth = int(orig_bw)
            sdr_instance.gain_control_mode_chan0 = orig_gain_mode
            if orig_gain_mode == "manual":
                sdr_instance.rx_hardwaregain_chan0 = int(orig_gain)
            time.sleep(0.02)
        except Exception as e:
            logger.warning("Gagal merestorasi konfigurasi Pluto asli: %s", e)

        if owns_sdr:
            try:
                sdr_instance.rx_destroy_buffer()
            except Exception:
                pass

    # 5. Klasifikasi Berdasarkan Pola Spektral
    res_text, ant_type, conf, summary, rec = classify_antenna_from_measurements(measurements)

    logger.info("Hasil Klasifikasi Antena: %s (Confidence: %.1f%%)", res_text, conf)

    return AntennaClassification(
        result_text=res_text,
        antenna_type=ant_type,
        confidence_pct=conf,
        summary=summary,
        recommendation=rec,
        measurements=measurements,
        timestamp=time.time(),
    )
