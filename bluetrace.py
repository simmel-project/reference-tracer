### BLUETRACE SERVER
import _bleio
from binascii import unhexlify, hexlify
import board
import digitalio
import gc
import microcontroller
import os
import struct
import random
import rtc
import time
import watchdog

###################### CONFIGURATION SECTION ######################

# This is the UUID we will be advertising for. This is dependent on your contact
# tracing implementation.
bluetrace_uuid = "f918c24c09fef0806a4f9515fcb32ab8"

# The number of seconds before the watchdog timer resets the system
watchdog_timeout_s = 300

# This string is used for advertising. It can be set to `None` to disable named
# broadcasts and increase anonymity.
adapter_name = "Simmel"

# The maximum amount of time to advertise for
advertising_timeout_s = 10

# How long to wait before we time out a scan
scan_timeout_s = 3

# Number of seconds before we disconnect from a connected client. Normally
# connections are long-lived, however since we can only service a few
# connections at a time, keep this number small.
connection_timeout_s = 5.0

######################### STARTUP SECTION #########################

# Enable the watchdog timer, if it isn't already enabled. We must feed it once
# every 300 seconds, or else the system will reboot. That way, if the system
# locks up, it will reboot back into a known good state. The watchdog timer will
# already be enabled if `code.py` is getting reloaded.
wdt = microcontroller.watchdog
if wdt.mode != watchdog.WatchDogMode.RESET:
    wdt.timeout = watchdog_timeout_s
    wdt.mode = watchdog.WatchDogMode.RESET

# Set the time based on the creation of this file. If the system time is earlier
# than the modification timestamp of this file, then assume the clock is
# incorrect and set it to this file. If the user has just copied code.py to
# their device, or if you have just saved file, then this timestamp should be
# accurate.
system_rtc = rtc.RTC()
did_set_time = False
code_py_time = os.stat("/code.py")[8]
if code_py_time > time.time():
    print("Setting time based on the timestamp of /code.py")
    did_set_time = True
    system_rtc.datetime = time.localtime(os.stat("/code.py")[8])

# Tie various signals low to prevent them from floating. This lowers power
# consumption for the system as a whole due to outputs triggering undesirable
# beavior. For example, a floating line will prevent the microphone from
# sleeping.
cs = digitalio.DigitalInOut(board.SPI_CSN)
cs.switch_to_output(value=True)

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output(value=False)

i2s_lrck = digitalio.DigitalInOut(board.I2S_LRCK)
i2s_lrck.switch_to_output(value=False)

i2s_sck = digitalio.DigitalInOut(board.I2S_SCK)
i2s_sck.switch_to_output(value=False)

bluetrace_uuid_bin = unhexlify(bluetrace_uuid)
bluetrace_uuid = _bleio.UUID(bluetrace_uuid_bin)

# Note that the txpower octet (02 0a 00) indicates we're transmitting at 0dBm,
# which is the default transmission power on an nRF52833. There is not yet an
# API available to change this parameter, so it is safe to hardcode it.
advertising_data = b'' \
    + unhexlify('1107') + bluetrace_uuid_bin \
    + unhexlify('020106') \
    + unhexlify('020a00') \
    + unhexlify('06ffff03') + bytearray([
        random.randint(0,256),
        random.randint(0,256),
        random.randint(0,256),
    ]) \
    + b''

# Dummy function to get the random token. This ordinarily would come from an
# HMAC, or pull OTP tokens from storage.
def get_random_token(bytes):
    rt = bytearray(bytes)
    # Fill the token in 8 bits at a time
    for i in range(bytes):
        rt[i] = random.getrandbits(8)
    return rt

adapter = _bleio.adapter
if adapter_name is not None:
    adapter.name = adapter_name
else:
    adapter.name = ""

# Convert the adapter name into a scan response, so it shows up as something
# other than "N/A".
scan_response = None
if adapter_name is not None:
    adapter_name_bytes= adapter_name.encode("utf-8")
    scan_response = bytearray([len(adapter_name_bytes) + 1, 8]) + adapter_name_bytes

# Create the BLE service that other devices will connect to in order to discover
# our contact tracing token.
bt_service = _bleio.Service(bluetrace_uuid, secondary=False)
print("Advertising data: ", hexlify(advertising_data))
def bind_to_service(service, uuid, token):
    properties = _bleio.Characteristic.READ | _bleio.Characteristic.WRITE
    read_perm = _bleio.Attribute.OPEN
    write_perm = _bleio.Attribute.OPEN
    return _bleio.Characteristic.add_to_service(
        service,
        uuid,
        initial_value = token,
        max_length = len(token),
        fixed_length = True,
        properties = properties,
        read_perm = read_perm,
        write_perm = write_perm
    )

# Bind our UUID to a characteristic, which is how we communicate with other
# devices using this particular GATT.
characteristic = bind_to_service(bt_service, bluetrace_uuid, get_random_token(160))
characteristic_buffer = _bleio.CharacteristicBuffer(characteristic, buffer_size=160)

loops = 0

def run_server(adapter, loops, characteristic_buffer):
    adapter.start_advertising(
        advertising_data,
        scan_response = scan_response,
        connectable = True,
        anonymous = True,
        timeout = advertising_timeout_s,
        interval = 0.1,
    )
    adapter_address = adapter.address
    print("Waiting for connection...")
    did_print_wc = False
    while not adapter.connected and adapter.enabled and adapter.advertising:
        did_print_wc = True
        dt = system_rtc.datetime # This leaks memory
        loops = loops + 1
        wdt.feed()
        print("\r WC | ",
            dt.tm_mday, "/", dt.tm_mon, "/", dt.tm_year, " ", dt.tm_hour, ":", dt.tm_min, ":", dt.tm_sec,
            "  Uptime: ", time.monotonic(),
            "  Loops? ", loops,
            "  GC? ", gc.mem_alloc(), "/", gc.mem_free(),
            "  Buffer? ", characteristic_buffer.in_waiting > 0,
            "  Address: ", adapter_address,
            "      ",
            end="", sep="")
        time.sleep(1)
    if did_print_wc:
        print("")
    print("    | Connected?", adapter.connected,
               " Enabled?", adapter.enabled,
               " Buffer?", characteristic_buffer.in_waiting)
    adapter.stop_advertising()

    connection_s = 0
    did_print_cn = False
    while adapter.connected and connection_s < connection_timeout_s:
        did_print_cn = True
        dt = system_rtc.datetime # This leaks memory
        loops = loops + 1
        wdt.feed()
        print("\r CN | ",
            dt.tm_mday, "/", dt.tm_mon, "/", dt.tm_year, " ", dt.tm_hour, ":", dt.tm_min, ":", dt.tm_sec,
            "  Uptime: ", time.monotonic(),
            "  Loops? ", loops,
            "  GC? ", gc.mem_alloc(), "/", gc.mem_free(),
            "  Buffer? ", characteristic_buffer.in_waiting > 0,
            "  Address: ", adapter_address,
            "      ",
            end="", sep="")
        if connection_s >= connection_timeout_s:
            print("")
            print("    ! Connection timed out, forcing disconnection", end="")
            break
        time.sleep(1)
        connection_s = connection_s + 1
    if did_print_cn:
        print("")
    for connection in adapter.connections:
        connection.disconnect()
    print("    o Disconnected from other device")
    return loops

def run_client(adapter, loops, bluetrace_uuid_bin, found_current, found_previous, scan_timeout, scan_interval=0.1):
    def find_rand_hash(buf):
        """Find the random hash that's part of the BlueTrace broadcast
        This is an optimization that allows us to skip the negoation if
        we've seen this device already."""
        offset = 0
        while offset < len(buf):
            size = buf[offset]
            typ = buf[offset + 1]
            if typ != 0xff:
                offset += size + 1
                continue
            if buf[offset + 2] != 0xff or buf[offset + 3] != 0x03:
                offset += size + 1
                continue
            val = int.from_bytes(buf[offset+4:offset+4+(size-4)+1], 'little')
            return val

            offset += size + 1
        return 0

    def print_hex_block(prefix, data):
        width=32
        print(prefix, end="")
        prefix = "    |" + " "*(len(prefix)-5)
        print(str(hexlify(data[0:width])).split("'")[1])
        for offset in range(width, len(data), width):
            print(prefix, end="")
            print(str(hexlify(data[offset:offset+width])).split("'")[1])

    print("Scanning for BlueTrace")
    for entry in adapter.start_scan(
            prefixes=b"\x00",
            buffer_size=1024,
            extended=False,
            timeout=scan_timeout,
            interval=scan_interval,
            window=0.1,
            minimum_rssi=-80,
            active=True,
    ):
        if bluetrace_uuid_bin in entry.advertisement_bytes:
            try:
                rand_hash = find_rand_hash(entry.advertisement_bytes)
                # If the random has is in the `found_current` set, then we've
                # seen it already. Skip it.
                if rand_hash in found_current:
                    continue

                print("Discovered  Addr:", entry.address,
                                 " Bytes:", hexlify(entry.advertisement_bytes),
                                 " RSSI:", entry.rssi)
                print("    |      This is a BlueTrace device!")
                print("    |      Random hash ID:", rand_hash)
                print("    |      Connecting...")
                connection = adapter.connect(entry.address, timeout=5)
                if not connection.connected:
                    print("    |      Couldn't connect, will try again")
                    continue
                print("    |      Device reported a connection was opened")

                # Once a connection is made, the scanning service will hang if
                # we try to resume scanning
                adapter.stop_scan()

                services = connection.discover_remote_services((bluetrace_uuid,))
                if len(services) > 0:
                    bluetrace_service = services[0]
                    print("    |      Enumerating GATT characteristics...")
                    ch = bluetrace_service.characteristics[0]
                    print("    |      BLE Properties: 0x{:x}".format(ch.properties))
                    print_hex_block("    |      Bluetrace Data (AES encrypted, {} bytes): ".format(len(ch.value)), ch.value)
                else:
                    print("Bluetrace UUID NOT FOUND")
                found_current.add(rand_hash)
            except Exception as e:
                print("    x      Error while communicating with device: {}".format(e))
                continue
    adapter.stop_scan()
    return loops + 1

discovered_current = set()
discovered_previous = set()

while True:
    loops = run_client(adapter, loops, bluetrace_uuid_bin, discovered_current, discovered_previous, scan_timeout_s)
    loops = run_server(adapter, loops, characteristic_buffer)
