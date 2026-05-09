"""
ECUシミュレータ (DoIP over TCP / ISO 13400-2)

対応SID:
  - 0x10 DiagnosticSessionControl
  - 0x11 ECUReset
  - 0x14 ClearDiagnosticInformation
  - 0x19 ReadDTCInformation (0x02/0x0A)
  - 0x22 ReadDataByIdentifier
  - 0x2E WriteDataByIdentifier
  - 0x31 RoutineControl (0x01/0x02/0x03)
  - 0x3E TesterPresent

起動方法:
  python ecu_simulator.py               # 127.0.0.1:13400
  python ecu_simulator.py --port 15740  # ポート指定
"""
import socket
import struct
import threading
import argparse

# ── DoIP定数 ──────────────────────────────────────────────────────────
DOIP_VERSION         = 0x02
DOIP_VERSION_INVERSE = 0xFD
PAYLOAD_TYPE_ROUTING_REQ  = 0x0005
PAYLOAD_TYPE_ROUTING_RESP = 0x0006
PAYLOAD_TYPE_DIAG         = 0x8001
PAYLOAD_TYPE_DIAG_ACK     = 0x8002
ROUTING_RESP_SUCCESS = 0x10

# ── UDS SID ────────────────────────────────────────────────────────────
SID_DSC_REQ   = 0x10;  SID_DSC_RESP  = 0x50
SID_RESET_REQ = 0x11;  SID_RESET_RESP= 0x51
SID_CLEAR_REQ = 0x14;  SID_CLEAR_RESP= 0x54
SID_RDTC_REQ  = 0x19;  SID_RDTC_RESP = 0x59
SID_RDBI_REQ  = 0x22;  SID_RDBI_RESP = 0x62
SID_WDBI_REQ  = 0x2E;  SID_WDBI_RESP = 0x6E
SID_RC_REQ    = 0x31;  SID_RC_RESP   = 0x71
SID_TP_REQ    = 0x3E;  SID_TP_RESP   = 0x7E
SID_NEGATIVE  = 0x7F

NRC_SUB_FUNCTION_NOT_SUPPORTED = 0x12
NRC_REQUEST_OUT_OF_RANGE       = 0x31
NRC_SERVICE_NOT_SUPPORTED      = 0x11
SUPPRESS_RESPONSE_BIT          = 0x80

# ── テスト用データ ─────────────────────────────────────────────────────
SUPPORTED_SESSIONS = {0x01, 0x02, 0x03}
VALID_RESET_TYPES  = {0x01, 0x03}

DID_TABLE: dict[int, bytes] = {
    0xF190: b"SIMVIN0000000001",
    0xF18C: b"SN-ECU-0042",
    0xF186: bytes([0x01]),
}

# 書き込み可能DID
WRITABLE_DIDS = {0xF190}

# ダミーDTCデータ: DTC(3bytes) + status(1byte)
DTC_RECORDS = bytes([
    0x01, 0x23, 0x45, 0x08,   # DTC=0x012345, status=0x08 (confirmed)
    0x00, 0xAB, 0xCD, 0x09,   # DTC=0x00ABCD, status=0x09
])

# サポートするルーティン
SUPPORTED_ROUTINES = {0x0201, 0xFF00}


# ── DoIPフレーム生成 ────────────────────────────────────────────────────

def _make_header(payload_type: int, length: int) -> bytes:
    return struct.pack(">BBHI", DOIP_VERSION, DOIP_VERSION_INVERSE, payload_type, length)

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


# ── UDS応答 ────────────────────────────────────────────────────────────

def handle_uds(uds_payload: bytes) -> bytes | None:
    sid = uds_payload[0]

    # 0x10 DiagnosticSessionControl
    if sid == SID_DSC_REQ:
        session_type = uds_payload[1] & 0x7F if len(uds_payload) > 1 else 0
        if session_type not in SUPPORTED_SESSIONS:
            return bytes([SID_NEGATIVE, sid, NRC_SUB_FUNCTION_NOT_SUPPORTED])
        return bytes([SID_DSC_RESP, session_type, 0x00, 0x19, 0x01, 0xF4])

    # 0x11 ECUReset
    elif sid == SID_RESET_REQ:
        reset_type = uds_payload[1] & 0x7F if len(uds_payload) > 1 else 0
        if reset_type not in VALID_RESET_TYPES:
            return bytes([SID_NEGATIVE, sid, NRC_SUB_FUNCTION_NOT_SUPPORTED])
        return bytes([SID_RESET_RESP, reset_type])

    # 0x14 ClearDiagnosticInformation
    elif sid == SID_CLEAR_REQ:
        return bytes([SID_CLEAR_RESP])

    # 0x19 ReadDTCInformation
    elif sid == SID_RDTC_REQ:
        subfn = uds_payload[1] & 0x7F if len(uds_payload) > 1 else 0
        status_mask = uds_payload[2] if len(uds_payload) > 2 else 0xFF
        if subfn == 0x02:
            return bytes([SID_RDTC_RESP, subfn, 0xFF]) + DTC_RECORDS
        elif subfn == 0x0A:
            return bytes([SID_RDTC_RESP, subfn, 0xFF]) + DTC_RECORDS
        return bytes([SID_NEGATIVE, sid, NRC_SUB_FUNCTION_NOT_SUPPORTED])

    # 0x22 ReadDataByIdentifier
    elif sid == SID_RDBI_REQ:
        if len(uds_payload) < 3:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        did = (uds_payload[1] << 8) | uds_payload[2]
        if did in DID_TABLE:
            return bytes([SID_RDBI_RESP]) + struct.pack(">H", did) + DID_TABLE[did]
        return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])

    # 0x2E WriteDataByIdentifier
    elif sid == SID_WDBI_REQ:
        if len(uds_payload) < 3:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        did = (uds_payload[1] << 8) | uds_payload[2]
        if did not in WRITABLE_DIDS:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        # 書き込み値をDIDテーブルに反映
        DID_TABLE[did] = uds_payload[3:]
        return bytes([SID_WDBI_RESP]) + struct.pack(">H", did)

    # 0x31 RoutineControl
    elif sid == SID_RC_REQ:
        subfn = uds_payload[1] & 0x7F if len(uds_payload) > 1 else 0
        if subfn not in {0x01, 0x02, 0x03}:
            return bytes([SID_NEGATIVE, sid, NRC_SUB_FUNCTION_NOT_SUPPORTED])
        if len(uds_payload) < 4:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        routine_id = (uds_payload[2] << 8) | uds_payload[3]
        if routine_id not in SUPPORTED_ROUTINES:
            return bytes([SID_NEGATIVE, sid, NRC_REQUEST_OUT_OF_RANGE])
        status_record = bytes([0x00]) if subfn == 0x03 else b""
        return bytes([SID_RC_RESP, subfn]) + struct.pack(">H", routine_id) + status_record

    # 0x3E TesterPresent
    elif sid == SID_TP_REQ:
        sub_fn = uds_payload[1] if len(uds_payload) > 1 else 0x00
        if sub_fn & SUPPRESS_RESPONSE_BIT:
            return None
        return bytes([SID_TP_RESP, 0x00])

    else:
        return bytes([SID_NEGATIVE, sid, NRC_SERVICE_NOT_SUPPORTED])


# ── 受信・クライアントハンドラ ─────────────────────────────────────────

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
            _ver, _inv, payload_type, payload_length = struct.unpack_from(">BBHI", header_data)
            payload = _recv_exact(conn, payload_length) if payload_length > 0 else b""
            if payload is None:
                break
            print(f"[SIM] RX type={hex(payload_type)} payload={payload.hex(' ').upper()}")

            if payload_type == PAYLOAD_TYPE_ROUTING_REQ:
                client_addr = struct.unpack_from(">H", payload, 0)[0]
                conn.sendall(build_routing_activation_response(client_addr, server_logical_addr))
                print(f"[SIM] TX RoutingActivationResponse OK client={hex(client_addr)}")

            elif payload_type == PAYLOAD_TYPE_DIAG:
                src = struct.unpack_from(">H", payload, 0)[0]
                tgt = struct.unpack_from(">H", payload, 2)[0]
                uds = payload[4:]
                conn.sendall(build_diagnostic_ack(tgt, src))
                uds_resp = handle_uds(uds)
                if uds_resp is not None:
                    conn.sendall(build_diagnostic_response(uds_resp, tgt, src))
                    print(f"[SIM] TX DiagnosticResponse: {uds_resp.hex(' ').upper()}")
                else:
                    print("[SIM] TX suppressed")
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
    print(f"[SIM] Listening on {host}:{port}  logical_addr={hex(server_logical_addr)}")
    print(f"[SIM] DIDs:     {', '.join(hex(d) for d in DID_TABLE)}")
    print(f"[SIM] Sessions: {', '.join(hex(s) for s in SUPPORTED_SESSIONS)}")
    print(f"[SIM] Routines: {', '.join(hex(r) for r in SUPPORTED_ROUTINES)}")
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
