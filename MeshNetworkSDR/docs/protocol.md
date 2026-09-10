# Packet Protocol Specification

## Frame Format

```text
┌──────────┬────────┬──────────┬──────────┬────────┐
│ Preamble │ Header │ Sequence │ Payload  │ CRC    │
└──────────┴────────┴──────────┴──────────┴────────┘
```

1. **Preamble**: Synchronization training sequences for packet detection.
2. **Header**:
   - `version` (8 bits)
   - `packet_type` (8 bits)
   - `payload_length` (16 bits)
   - `sequence_number` (32 bits)
   - `modulation` (8 bits)
   - `coding_rate` (8 bits)
3. **Sequence Number**: Packet ordering and loss detection.
4. **Payload**: User/IP packet payload (MTU up to 1024 bytes).
5. **CRC**: Standard 32-bit CRC checksum.
