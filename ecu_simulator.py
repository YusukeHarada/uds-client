"""
ECUシミュレータ (DoIP over TCP / ISO 13400-2)

実ECUなしでローカル結合テスト・CLI手動確認ができるシミュレータ。
doipclientが要求するRoutingActivationハンドシェイクに対応。

起動方法:
  python ecu_simulator.py               # 127.0.0.1:13400
  python ecu_simulator.py --port 15740  # ポート指定

テスト用DIDテーブル:
  F190: VIN
  F18C: ECU Serial Number
  F186: Active Diagnostic Session
"""

import socket
import struct
import threading
import argparse

DOIP_VERSION         = 0x02
DOIP_VERSION_INVERSE = 0xFD
PAYLOAD_TYPE_ROUTING_REQ  = 0x0005
PAYLOAD_TYPE_ROUTING_RESP = 0x0006
PAYLOAD_TYPE_DIAG         = 0x8001
PAYLOAD_TYPE_DIAG_ACK     = 0x8002
ROUTING_RESP_SUCCESS = 0x10

SID_RDBI_REQ  = 0x22
SID_RDBI_RESP = 0x62
SID_NEGATIVE  = 0x7F
NRC_REQUEST_OUT_OF_RANGE  = 0x31
NRC_SERVICE_NOT_SUPPORTED = 0x11

DID_TABLE: dict[int, bytes] = {
    0xF190: b"SIMVIN0000000001",
    0xF18C: b"SN-ECU-0042",
    0xF186: bytes([0x01]),
}


def _make_header(payload_type: int, payload_length: int) -> bytes:
    return struct.pack(">BBHI", DOIP_VERSION, DOIP_VERSION_INVERSE,
                       payload_type, payload_length)


def build_routing_activation_response(client_addr: int, server_addr: int) -> bytes:
    payload = struct.pack(">HHBL", client_addr, server_addr, ROUTING_RESP_SUCCESS, 0)
    return _make_header(PAYLOAD_TYPE_ROUTING_RESP, len(payload)) + payload


def build_diagnostic_ack(source: int, target: int) -> bytes:
    payload = struct.pack(">HHB", source, target, 0x00)
    return _make_header(PAYLOAD_TYPE_DIAG_ACK, len(payload)) + payload


def build_diagnostic_response(uds_payload: bytes, source: int, target: int) -> bytes:
    addr = struct.pack(">HH", source, target)
    payload = addr + uds_payload
    return _make_header(PAYLOAD_TYPE_DIAG, len(payload)) + payload


def handle_uds(uds_payload: bytes) -> bytes:
    sid = uds_payload[0]
    if sid == SID_RDBI_REQ:
        if len(uds_payload) < 3:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        did = (uds_payload[1] << 8) | uds_payload[2]
        if did in DID_TABLE:
            return bytes([SID_RDBI_RESP]) + struct.pack(">H", did) + DID_TABLE[did]
        return bytes([SID_NEGATIVE, SID_RDBI_REQ, NRC_REQUEST_OUT_OF_RANGE])
    return bytes([SID_NEGATIVE, sid, NRC_SERVICE_NOT_SUPPORTED])


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def handle_client(conn: socket.socket, addr: tuple,
                  server_logical_addr: int = 0x1000) -> None:
    print(f"[SIM] Connected: {addr}")
    try:
        while True:
            header_data = _recv_exact(conn, 8)
            if not header_data:
                break

            _ver, _inv, payload_type, payload_length = struct.unpack_from(
                ">BBHI", header_data, 0
            )
            payload = _recv_exact(conn, payload_length) if payload_length > 0 else b""
            if payload is None:
                break

            print(f"[SIM] RX type={hex(payload_type)} "
                  f"payload={payload.hex(' ').upper()}")

            if payload_type == PAYLOAD_TYPE_ROUTING_REQ:
                client_addr = struct.unpack_from(">H", payload, 0)[0]
                resp = build_routing_activation_response(
                    client_addr, server_logical_addr
                )
                conn.sendall(resp)
                print(f"[SIM] TX RoutingActivationResponse OK "
                      f"client={hex(client_addr)}")

            elif payload_type == PAYLOAD_TYPE_DIAG:
                src = struct.unpack_from(">H", payload, 0)[0]
                tgt = struct.unpack_from(">H", payload, 2)[0]
                uds = payload[4:]
                conn.sendall(build_diagnostic_ack(tgt, src))
                uds_resp = handle_uds(uds)
                conn.sendall(build_diagnostic_response(uds_resp, tgt, src))
                print(f"[SIM] TX DiagnosticResponse: {uds_resp.hex(' ').upper()}")
            else:
                print(f"[SIM] Unhandled payload_type={hex(payload_type)}")

    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        conn.close()
        print(f"[SIM] Disconnected: {addr}")


def run_server(host: str = "127.0.0.1", port: int = 13400,
               server_logical_addr: int = 0x1000,
               stop_event: threading.Event | None = None) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    server.settimeout(1.0)
    print(f"[SIM] Listening on {host}:{port}  "
          f"logical_addr={hex(server_logical_addr)}")
    print(f"[SIM] DIDs: {', '.join(hex(d) for d in DID_TABLE)}")
    if not stop_event:
        print("[SIM] Ctrl+C to stop\n")
    try:
        while not (stop_event and stop_event.is_set()):
            try:
                conn, addr = server.accept()
                threading.Thread(
                    target=handle_client,
                    args=(conn, addr, server_logical_addr),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n[SIM] Shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDS ECU Simulator (DoIP)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=13400)
    args = parser.parse_args()
    run_server(args.host, args.port)
