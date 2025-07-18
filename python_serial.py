#!/usr/bin/env python3
"""
Cross-platform serial communication tool and importable module for flexible serial I/O.

Provides a `SerialCommunicator` class for embedding in your Python projects,
plus a script entry point for CLI use. All key functions are exposed at module level for convenience.
"""
import argparse
import threading
import time
import sys
import logging
import string
import os

# Optional readline for command history
try:
    import readline
except ImportError:
    pass

try:
    import serial
    from serial import SerialException
except ImportError:
    raise ImportError("pyserial is required. Install with: pip install pyserial")


def parse_delay(x: str) -> float:
    try:
        if x.endswith("ms"):
            return float(x[:-2]) / 1000.0
        if x.endswith("s"):
            return float(x[:-1])
        if x.endswith("m") and not x.endswith("ms"):
            return float(x[:-1]) * 60.0
        if x.endswith("h"):
            return float(x[:-1]) * 3600.0
        return float(x) / 1000.0
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid time value: {x}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Feature-rich serial communicator with output format control and logging."
    )
    parser.add_argument(
        "-p", "--port", required=True, help="Serial port (e.g., COM3 or /dev/ttyUSB0)"
    )
    parser.add_argument(
        "-b", "--baudrate", type=int, default=9600, help="Baud rate (default: 9600)"
    )
    parser.add_argument(
        "--parity",
        choices=["N", "E", "O", "M", "S"],
        default="N",
        help="Parity: N=None, E=Even, O=Odd, M=Mark, S=Space",
    )
    parser.add_argument(
        "--stopbits",
        type=float,
        choices=[1, 1.5, 2],
        default=1,
        help="Stop bits (default: 1)",
    )
    parser.add_argument(
        "--bytesize",
        type=int,
        choices=[5, 6, 7, 8],
        default=8,
        help="Byte size (default: 8)",
    )
    parser.add_argument("-l", "--log-file", help="Path to log file for comms")
    parser.add_argument(
        "--log-format",
        choices=["plain", "json", "csv"],
        default="plain",
        help="Log file format (default: plain)",
    )
    parser.add_argument(
        "--no-log-sent", action="store_true", help="Don't log sent messages"
    )
    parser.add_argument(
        "-m",
        "--message",
        help="Message to send on startup (prefix 0x/0b/0o for non-ASCII)",
    )
    parser.add_argument(
        "-s",
        "--spam",
        nargs="?",
        const=-1,
        type=lambda x: int(x, 0),
        default=1,
        help="Repeat count: no value = infinite, e.g. -s or --spam 5",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=parse_delay,
        default=parse_delay("1"),
        help="Delay between spams (default: 1ms), suffix ms/s/m/h",
    )
    parser.add_argument("--send-file", help="Send raw bytes from file and exit")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show raw hex dumps"
    )
    parser.add_argument(
        "--out-format",
        choices=["autodetect", "ascii", "hex", "bin", "oct"],
        default="autodetect",
        help="Incoming data display format",
    )


def setup_logger(path, fmt):
    logger = logging.getLogger("serial_comm")
    logger.setLevel(logging.INFO)
    if not path:
        return None
    if fmt == "csv":
        fmt_str = "%(asctime)s,%(message)s"
    elif fmt == "json":
        fmt_str = '{"timestamp":"%(asctime)s","msg":"%(message)s"}'
    else:
        fmt_str = "%(asctime)s - %(message)s"
    fh = logging.FileHandler(path)
    fh.setFormatter(logging.Formatter(fmt_str))
    logger.addHandler(fh)
    return logger


class SerialCommunicator:
    def __init__(
        self,
        port,
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
        out_format="autodetect",
        log_file=None,
        log_format="plain",
        no_log_sent=False,
        verbose=False,
    ):
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=0.1,
        )
        self.out_format = out_format
        self.logger = setup_logger(log_file, log_format)
        self.log_sent = not no_log_sent
        self.verbose = verbose
        self._stop_event = threading.Event()

    @staticmethod
    def encode(msg: str) -> bytes:
        if msg.startswith(("0x", "0X")):
            hexstr = msg[2:]
            if len(hexstr) % 2:
                hexstr = "0" + hexstr
            return bytes.fromhex(hexstr)
        if msg.startswith(("0b", "0B")):
            b = msg[2:]
            b = b.zfill((len(b) + 7) // 8 * 8)
            return int(b, 2).to_bytes(len(b) // 8, "big")
        if msg.startswith(("0o", "0O")):
            val = int(msg[2:], 8)
            return val.to_bytes((val.bit_length() + 7) // 8, "big")
        return msg.encode("ascii")

    @staticmethod
    def format_fixed(data: bytes, fmt: str) -> str:
        try:
            if fmt == "ascii":
                return data.decode("ascii")
            if fmt == "hex":
                return "0x" + data.hex()
            if fmt == "bin":
                return "0b" + "".join(f"{b:08b}" for b in data)
            if fmt == "oct":
                return "0o" + "".join(f"{b:03o}" for b in data)
        except Exception:
            return "<format-error>"
        return "<unsupported-format>"

    @staticmethod
    def format_auto(data: bytes) -> str:
        try:
            s = data.decode("ascii")
            if all(c in string.printable for c in s):
                return s
        except Exception:
            pass
        return "0x" + data.hex()

    def _apply_format(self, data: bytes) -> str:
        if self.out_format != "autodetect":
            return self.format_fixed(data, self.out_format)
        return self.format_auto(data)

    def start_reader(self):
        def reader():
            while not self._stop_event.is_set():
                waiting = self._ser.in_waiting
                if waiting:
                    data = self._ser.read(waiting)
                    out = self._apply_format(data).rstrip("\r\n")
                    if not out:
                        continue
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    if self.verbose:
                        print(f"[{ts}] REC RAW: 0x{data.hex()}")
                    print(f"[{ts}] REC: {out}")
                    if self.logger:
                        self.logger.info(f"RECV,{data.hex()}")
                else:
                    time.sleep(0.1)

        self._thread = threading.Thread(target=reader, daemon=True)
        self._thread.start()

    def send(self, payload: bytes, count=1, delay=0.0):
        i = 0
        infinite = count < 0
        while infinite or i < count:
            self._ser.write(payload)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            out = self._apply_format(payload)
            if self.verbose:
                print(f"[{ts}] SEND RAW: 0x{payload.hex()}")
            print(f"[{ts}] SEND: {out}")
            if self.logger and self.log_sent:
                self.logger.info(f"SENT,{payload.hex()}")
            i += 1
            time.sleep(delay)

    def close(self):
        self._stop_event.set()
        if hasattr(self, "_thread"):
            self._thread.join(timeout=1)
        self._ser.close()


# Module-level aliases for convenience
encode = SerialCommunicator.encode
format_fixed = SerialCommunicator.format_fixed
format_auto = SerialCommunicator.format_auto

# CLI entry point
if __name__ == "__main__":
    args = parse_args()
    comm = SerialCommunicator(
        port=args.port,
        baudrate=args.baudrate,
        parity=args.parity,
        stopbits=args.stopbits,
        bytesize=args.bytesize,
        out_format=args.out_format,
        log_file=args.log_file,
        log_format=args.log_format,
        no_log_sent=args.no_log_sent,
        verbose=args.verbose,
    )
    comm.start_reader()
    if args.send_file:
        with open(args.send_file, "rb") as f:
            data = f.read()
        comm.send(data, args.spam, args.delay)
    elif args.message:
        data = encode(args.message)
        comm.send(data, args.spam, args.delay)
    else:
        try:
            while True:
                msg = input("> ").strip()
                if msg.lower() in ("exit", "quit"):
                    break
                if not msg:
                    continue
                data = encode(msg)
                comm.send(data, args.spam, args.delay)
        except (KeyboardInterrupt, EOFError):
            pass
    comm.close()
