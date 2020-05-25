# Simmel Reference Tracer

Simmel is designed to be easily adaptable to any contact tracing
implementation. This project represents a reference implementation of one
possible contact tracing system.

It is based on Singapore's TraceTogether project.

## Software Support

This relies on Circuit Python for NRF boards, such as [Circuit Python for Simmel](https://circuitpython.org/board/simmel/). Ensure you have this installed on your device, then copy `code.py` over to it. You can use the USB terminal to interact with it or to monitor tracing.

## Installation

To install, rename `bluetrace.py` to `code.py` and drag it on to
the Simmel flash drive.

You can monitor the output by attaching a serial console to the virtual
USB serial port.

## Example Output

This program scans for nearby devices, and queries their service for
their token. If a token is brand-new, it displays it on the screen. In
the TraceTogether system (known as BlueTrace), tokens are valid for
fifteen minutes.

After scanning, it begins advertising its own token for a short time.
If a device connects, it will allow the remote device to communicate
with us, possibly sending us their own token.

This output shows the advertising data, a remote device's connection,
as well as what happens when a remote device connects to us. Finally,
it also shows that the RTC is functioning normally, and the garbage
collector is performing well.

```
Scanning for BlueTrace
Discovered  Addr: <Address 40:f7:31:36:24:a0>  Bytes: b'02010206ffff03383663020a041107f918c24c09fef0806a4f9515fcb32ab8'  RSSI: -58
    |      This is a BlueTrace device!
    |      Random hash ID: 6501944
    |      Connecting...
    |      Device reported a connection was opened
    |      Enumerating GATT characteristics...
    |      BLE Properties: 0x18
    |      Bluetrace Data (AES encrypted, 160 bytes): 9d1f382a95391c4eae1796905cc7a36081bdd102b64ec943e51a31230f2c7f76
                                                      2dbb7e4a7d4f70db0278e045d362059bee0a13d2baa307d85fc6e5049923afe4
                                                      e4f8e9db191802707799189176d2daf9185c16d7d8bfddacc3f2df2a777e1174
                                                      3cce8af9c5dbe6e60e121ab41b0fda350829acaa414ba8c576f9cff13c854af7
                                                      6fc4c8d628f3412bbd6478b18442bdc8d3f92dbf99ff7f760dd8e7598795342c
Waiting for connection...
    | Connected? True  Enabled? True  Buffer? 0
 CN | 25/5/2020 19:52:31  Uptime: 276015.0  Loops? 7048  GC? 26256/29616  Buffer? False  Address: <Address e7:a3:3a:9a:48:b2>
    o Disconnected from other device
Scanning for BlueTrace
Waiting for connection...
 WC | 25/5/2020 19:52:44  Uptime: 276028.0  Loops? 7059  GC? 38496/17376  Buffer? False  Address: <Address e7:a3:3a:9a:48:b2>
    | Connected? False  Enabled? True  Buffer? 0
    o Disconnected from other device
Scanning for BlueTrace
Waiting for connection...
 WC | 25/5/2020 19:52:51  Uptime: 276035.0  Loops? 7064  GC? 7952/47920  Buffer? False  Address: <Address e7:a3:3a:9a:48:b2>
```

Notice how the token is AES encrypted. This could be decrypted using
the `aesio` module, as long as we had the proper key. Likewise, we
could form our own messages using a known common AES key, which would
prevent us from having to store full encrypted data.

Alternatively, Simmel could store several months' worth of encrypted
tokens to transmit, and log encrypted tokens that it sees, all without
needing to deal with encryption keys.

## Potential Extensions

This is just a base. Additions would need to be made to create a full
contact tracing solution.

### Token Database

Simmel contains an onboard SPI flash device. This can be addressed using
ordinary Circuit Python classes. Raw SPI is ideal for logging this kind
of data, because this is almost entirely a write-only operation. SPI NOR
can be written without erasing, provided it has already been erased. This
means that many outgoing tokens can be loaded into this database, and then
those tokens can be erased to `zero` once they're used.

Similarly, discovered tokens can be added to a different part of flash,
and entire blocks of discovered tokens can be erased at once as soon as
they are no longer needed.

This allows for much tighter packing of tokens, and makes efficient use of
SPI NOR primitives.

### Serial Transfer

The virtual filesystem is only about 70 kilobytes. This filesystem is stored
on internal flash, in order to dedicate the SPI flash chip to contacts.
One way to load tokens onto and off of the SPI flash would be to use some
serial transfer protocol such as xmodem. Solutions exist, however they
need to be ported to Circuit Python.

## About the Simmel Project

The Simmel project was started on April 10, 2020 in response to a request for a hardware design proposal by NLNet. The Simmel project name comes from Georg Simmel, an early researcher into sociology and social distance theory.

<center><img src="https://nlnet.nl/logo/banner.png" width="20%"> <img src="https://nlnet.nl/image/logos/NGI0_tag.png" width="20%"></center>

The Simmel team is funded through the [NGI0 PET
Fund](https://nlnet.nl/PET), a fund established by NLnet with financial
support from the European Commission's [Next Generation
Internet](https://ngi.eu/) programme, under the aegis of DG
Communications Networks, Content and Technology under grant agreement No
825310.
