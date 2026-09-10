# Networking Architecture

## UDP Transport (Stage 6)

Direct socket integration transmitting packets from user space through the modem without elevated system privileges:

```text
App -> UDP Socket (port 5000) -> Modem TX -> RF -> Modem RX -> UDP Socket -> App
```

## TUN/TAP Interface (Stage 7)

Creation of a virtual network interface `radio0`:
- Node A IP: `192.168.50.1/24`
- Node B IP: `192.168.50.2/24`
- IP packets written to `radio0` are serialized by the Python SDR modem, modulated, transmitted, received, and delivered back to the kernel on the peer node.
