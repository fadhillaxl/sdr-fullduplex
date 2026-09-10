# Hardware & Driver Troubleshooting

## 1. Pluto SDR Not Detected

When running `python scripts/detect_pluto.py`:

```text
================================
PLUTO SDR
================================
Status       : NOT FOUND
================================
```

### Steps to Resolve:

1. **Verify USB Cable**: Many micro-USB cables are charge-only. Use a data cable.
2. **Scan IIO Contexts**:
   ```bash
   iio_info -s
   ```
   If no devices are listed, the OS does not see the Pluto USB interface.
3. **Check Network Interface**:
   By default, Pluto creates an Ethernet-over-USB network interface (`usb0` or `enx...`) with IP `192.168.2.1`. Ensure your host interface on that subnet is configured:
   ```bash
   ping 192.168.2.1
   ```
4. **Linux Permissions (udev)**:
   Add udev rules for ADALM-Pluto:
   ```bash
   sudo usermod -a -G plugdev,dialout $USER
   ```
