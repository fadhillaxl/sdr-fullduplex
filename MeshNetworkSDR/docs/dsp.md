# DSP Pipeline Specification

## Modulation Modes

### BPSK (Stage 2)
- 1 bit per symbol: maps $\{0, 1\} \to \{-1, +1\}$.
- Robust baseline for early packet link validation.

### QPSK (Stage 3)
- 2 bits per symbol with Gray coding mapping:
  - `00` $\to \frac{1}{\sqrt{2}}(+1 + 1j)$
  - `01` $\to \frac{1}{\sqrt{2}}(-1 + 1j)$
  - `11` $\to \frac{1}{\sqrt{2}}(-1 - 1j)$
  - `10` $\to \frac{1}{\sqrt{2}}(+1 - 1j)$

## OFDM Modem (Stage 4)

- **FFT Size**: 64 subcarriers.
- **Cyclic Prefix**: 16 samples.
- **Pilot Allocation**: Dedicated pilot subcarriers for coarse and fine channel estimation.
- **Synchronization**: Schmidl & Cox preamble autocorrelation for frame timing and Carrier Frequency Offset (CFO) estimation.
