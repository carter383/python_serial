# Serial Comm

## Why I Made This

While working on embedded systems projects, particularly with Arduino and microcontrollers, I constantly ran into a recurring need: send raw serial data quickly and flexibly during testing and debugging.

Existing tools were either too simplistic, offering no control over byte structure or encoding, or overly bloated, requiring GUI environments or custom protocol stacks. I wanted something:

- That works instantly from the terminal or shell script
- That could be dropped into automated test pipelines
- That understands different number bases like hex, binary, and octal natively
- That could log communication in multiple formats for analysis
- That can send the same message repeatedly, with fine-grained control over delay and format
- That can gracefully handle interactive sessions or scripted ones

So I built this. A single tool that combines the convenience of a command-line interface with the power of a full Python class interface. It is perfect for both quick tests and deeper integration into larger projects.

---

## Features

- **✅ CLI and Importable Module**  
  Use it as a standalone script for quick tasks or import it as a class into your Python applications for more control

- **🧠 Flexible Input Formats**  
  Send ASCII or binary data using intuitive prefixes:
  - `0xFF` for hexadecimal
  - `0b1010` for binary
  - `0o777` for octal
  - `Hello` for ASCII

- **📤 Custom Output Formatting**  
  Print received bytes as:
  - Readable ASCII (when printable)
  - Hexadecimal, binary, or octal
  - Or let it auto-detect the best format

- **🔧 Advanced Serial Settings**  
  Full control over low-level serial options like:
  - Baud rate
  - Parity bits (N, E, O, M, S)
  - Stop bits
  - Data byte size

- **📝 Logging**  
  Capture logs in real time:
  - Output to plain text, CSV, or structured JSON
  - Choose to include or exclude sent messages

- **🔁 Spam Mode**  
  Repeat any message:
  - A set number of times (e.g. 5 times)
  - Or infinitely until stopped manually

- **⏱️ Controlled Delays**  
  Wait between sends with fine-grained control:
  - Supports values like `100ms`, `1s`, `1m`, `1h`
  - Defaults to 1ms if no suffix is provided

- **📁 File Transfer**  
  Send raw binary files such as firmware or config blobs directly over serial

- **⚡ Cross-platform**  
  Works on Linux, Windows, and macOS with Python and pySerial

---

## 🚀 Running as CLI Tool

```bash
./python_serial.py -p PORT [options]
```

---

## 📦 Installation

```bash
pip install pyserial
```

Or clone manually:

```bash
git clone https://github.com/carter383/python_serial
cd python_serial
chmod +x python_serial.py
```

---

## 🔧 CLI Options

This tool provides a robust and flexible CLI interface with full control over serial communication and logging.

| **Option**         | **Description**                                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-p`, `--port`     | **Required.** Serial port to use — e.g., `COM3` on Windows or `/dev/ttyUSB0` on Linux.                                                             |
| `-b`, `--baudrate` | Baud rate for communication. Default: `9600`. Common values: `115200`, `57600`, etc.                                                               |
| `--parity`         | Parity bit configuration:<br>`N` = None, `E` = Even, `O` = Odd, `M` = Mark, `S` = Space.                                                           |
| `--stopbits`       | Stop bits: `1`, `1.5`, or `2`. Default: `1`.                                                                                                       |
| `--bytesize`       | Number of data bits: `5`, `6`, `7`, or `8`. Default: `8`.                                                                                          |
| `-m`, `--message`  | Message to send when script starts. Supports:<br>`0x` = hex, `0b` = binary, `0o` = octal, or plain ASCII.                                          |
| `-s`, `--spam [N]` | Repeated sending:<br>- Use `-s 5` to send 5 times<br>- Use `-s` with no value for infinite repeats.                                                |
| `-d`, `--delay`    | Delay between messages. Supports:<br>`ms`, `s`, `m`, `h`, or numeric value (interpreted as milliseconds).<br>Examples: `100ms`, `1s`, `0.5`, `2m`. |
| `--send-file`      | Path to a binary file to send over serial. Sends contents directly.                                                                                |
| `--out-format`     | Format to display received data:<br>`ascii`, `hex`, `bin`, `oct`, or `autodetect`.                                                                 |
| `--log-file`       | Path to a log file for storing communication.                                                                                                      |
| `--log-format`     | Format of the log output:<br>`plain`, `json`, or `csv`.                                                                                            |
| `--no-log-sent`    | Disable logging of sent messages (logs only incoming data).                                                                                        |
| `-v`, `--verbose`  | Enables verbose mode:<br>Shows both formatted and raw hex output.                                                                                  |
| `--tui`            | Launch curses-based real-time TUI (text-based user interface).                                                                                     |

---

## 📌 Examples

### Basic interactive usage:

```bash
./python_serial.py -p /dev/ttyUSB0
```

### Send hex data 5 times with 200ms delay:

```bash
./python_serial.py -p COM3 -m 0xABCD -s 5 -d 200ms
```

### Infinite ASCII spam every second:

```bash
./python_serial.py -p COM3 -m PING -s -d 1s
```

### Send a binary file:

```bash
./python_serial.py -p /dev/ttyUSB0 --send-file firmware.bin
```

### Log all serial traffic to a CSV file:

```bash
./python_serial.py -p COM3 --log-file session.csv --log-format csv
```

### Run in verbose mode with hex output:

```bash
./python_serial.py -p COM3 --out-format hex -v
```

### Send once without logging:

```bash
./python_serial.py -p COM3 -m TEST --no-log-sent
```

## 🔧 Using as a Python Module

```python
from python_serial import SerialCommunicator, encode
from logging import getLogger, basicConfig

# Setup logging
basicConfig(level="INFO")
logger = getLogger("serial_test")

# Initialize communicator
comm = SerialCommunicator(
    port='/dev/ttyUSB0',
    baudrate=115200,
    parity='N',
    stopbits=1,
    bytesize=8,
    out_format='hex',
    log_file='session.csv',
    log_format='csv',
    verbose=True
)

# Start reading
comm.start_reader()

# Send ASCII message
comm.send(encode("HELLO"))

# Send HEX five times with 200ms delay
comm.send(encode("0xDEADBE"), count=5, delay=0.2)

# Infinite binary spam every 1 second (Uncomment to run)
#comm.send(encode("0b10101010"), count=-1, delay=1.0)

# Send once without logging
comm.send(encode("0xBEEF"), count=1, log_sent=False)

# Clean up
comm.close()
```
