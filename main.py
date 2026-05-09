"""
CLIエントリポイント。

clickのサブコマンド方式でSIDを指定して実行する。
共通オプション（--ip / --port / --log / --logfile）はグループレベルで定義し、
コンテキスト経由で各サブコマンドに渡す。
"""
import sys
import click
from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol

DOIP_PORT = 13400


# ── 共通コンテキスト ───────────────────────────────────────────────────

@click.group()
@click.option("--ip",      required=True,  help="ECU IP address")
@click.option("--port",    default=DOIP_PORT, show_default=True, help="DoIP port")
@click.option("--log",     default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
              help="Log level")
@click.option("--logfile", default="uds_log.json", show_default=True,
              help="Log output file (JSON Lines)")
@click.pass_context
def cli(ctx, ip, port, log, logfile):
    """UDS診断ツール (DoIP)"""
    ctx.ensure_object(dict)
    ctx.obj["ip"]      = ip
    ctx.obj["port"]    = port
    ctx.obj["log"]     = log
    ctx.obj["logfile"] = logfile


# ── 接続ヘルパー ───────────────────────────────────────────────────────

def _connect(ctx) -> tuple[DiagnosticService, DoIPProtocol]:
    obj = ctx.obj
    protocol = DoIPProtocol(host=obj["ip"], port=obj["port"])
    try:
        protocol.connect()
    except OSError as e:
        click.echo(f"[ERROR] 接続失敗: {e}", err=True)
        sys.exit(1)
    service = DiagnosticService(
        protocol=protocol,
        log_path=obj["logfile"],
        log_level=obj["log"],
    )
    return service, protocol


def _disconnect(protocol: DoIPProtocol):
    try:
        protocol.disconnect()
    except Exception:
        pass


# ── SID 0x22 ReadDataByIdentifier ─────────────────────────────────────

@cli.command()
@click.argument("did")
@click.pass_context
def rdbi(ctx, did):
    """0x22 ReadDataByIdentifier  例: rdbi F190"""
    try:
        did_int = int(did, 16)
    except ValueError:
        click.echo(f"[ERROR] DIDの形式が不正です: {did}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.read_data_by_identifier(did=did_int)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        click.echo(f"[OK]  DID={hex(did_int)}  Data={result.data.hex(' ').upper()}")
    else:
        click.echo(f"[NRC] DID={hex(did_int)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x2E WriteDataByIdentifier ────────────────────────────────────

@cli.command()
@click.argument("did")
@click.option("--data", required=True, help="書き込みデータ (hex文字列 例: 4E455756494E)")
@click.pass_context
def wdbi(ctx, did, data):
    """0x2E WriteDataByIdentifier  例: wdbi F190 --data 4E455756494E"""
    try:
        did_int = int(did, 16)
    except ValueError:
        click.echo(f"[ERROR] DIDの形式が不正です: {did}", err=True)
        sys.exit(1)
    try:
        data_bytes = bytes.fromhex(data.replace(" ", ""))
    except ValueError:
        click.echo(f"[ERROR] dataの形式が不正です: {data}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.write_data_by_identifier(did=did_int, data=data_bytes)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        click.echo(f"[OK]  WriteDataByIdentifier DID={hex(did_int)}")
    else:
        click.echo(f"[NRC] DID={hex(did_int)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x10 DiagnosticSessionControl ─────────────────────────────────

@cli.command()
@click.argument("session_type")
@click.pass_context
def session(ctx, session_type):
    """0x10 DiagnosticSessionControl  例: session 03"""
    try:
        session_int = int(session_type, 16)
    except ValueError:
        click.echo(f"[ERROR] session_typeの形式が不正です: {session_type}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.change_session(session_type=session_int)
    except ValueError as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        click.echo(f"[OK]  Session={hex(result.session_type)}")
    else:
        click.echo(f"[NRC] Session={hex(session_int)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x3E TesterPresent ────────────────────────────────────────────

@cli.command("tester-present")
@click.option("--suppress", is_flag=True, default=False, help="suppress response")
@click.pass_context
def tester_present(ctx, suppress):
    """0x3E TesterPresent  例: tester-present [--suppress]"""
    service, protocol = _connect(ctx)
    try:
        result = service.tester_present(suppress_response=suppress)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        suffix = " (suppressed)" if suppress else ""
        click.echo(f"[OK]  TesterPresent{suffix}")
    else:
        click.echo(f"[NRC] TesterPresent  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x11 ECUReset ─────────────────────────────────────────────────

@cli.command()
@click.argument("reset_type", type=click.Choice(["hard", "soft"], case_sensitive=False))
@click.pass_context
def reset(ctx, reset_type):
    """0x11 ECUReset  例: reset hard / reset soft"""
    reset_map = {"hard": 0x01, "soft": 0x03}
    reset_int = reset_map[reset_type.lower()]

    service, protocol = _connect(ctx)
    try:
        result = service.ecu_reset(reset_type=reset_int)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        click.echo(f"[OK]  ECUReset type={reset_type} ({hex(reset_int)})")
    else:
        click.echo(f"[NRC] ECUReset  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x14 ClearDiagnosticInformation ───────────────────────────────

@cli.command("clear-dtc")
@click.option("--group", default="FFFFFF", show_default=True,
              help="GroupOfDTC (hex)  FFFFFF=全消去")
@click.pass_context
def clear_dtc(ctx, group):
    """0x14 ClearDiagnosticInformation  例: clear-dtc [--group FFFFFF]"""
    try:
        group_int = int(group, 16)
    except ValueError:
        click.echo(f"[ERROR] groupの形式が不正です: {group}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.clear_dtc(group_of_dtc=group_int)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        click.echo(f"[OK]  ClearDTC group={hex(group_int)}")
    else:
        click.echo(f"[NRC] ClearDTC  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


# ── SID 0x19 ReadDTCInformation ───────────────────────────────────────

@cli.command("read-dtc")
@click.option("--subfn", default="02", show_default=True,
              type=click.Choice(["02", "0a", "0A"], case_sensitive=False),
              help="SubFunction: 02=byStatusMask 0A=supportedDTC")
@click.option("--mask", default="FF", show_default=True, help="StatusMask (hex)")
@click.pass_context
def read_dtc(ctx, subfn, mask):
    """0x19 ReadDTCInformation  例: read-dtc --subfn 02 --mask FF"""
    try:
        subfn_int = int(subfn, 16)
        mask_int  = int(mask, 16)
    except ValueError as e:
        click.echo(f"[ERROR] 引数の形式が不正です: {e}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.read_dtc(subfunction=subfn_int, status_mask=mask_int)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if not result.success:
        click.echo(f"[NRC] ReadDTC  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)

    if not result.dtc_records:
        click.echo(f"[OK]  ReadDTC subfn={hex(subfn_int)}  DTCなし")
    else:
        click.echo(f"[OK]  ReadDTC subfn={hex(subfn_int)}  件数={len(result.dtc_records)}")
        for rec in result.dtc_records:
            click.echo(f"      {rec}")


# ── SID 0x31 RoutineControl ───────────────────────────────────────────

@cli.command()
@click.argument("subfn")
@click.argument("routine_id")
@click.pass_context
def routine(ctx, subfn, routine_id):
    """0x31 RoutineControl  例: routine 01 0201"""
    try:
        subfn_int = int(subfn, 16)
    except ValueError:
        click.echo(f"[ERROR] subfnの形式が不正です: {subfn}", err=True)
        sys.exit(1)
    try:
        routine_id_int = int(routine_id, 16)
    except ValueError:
        click.echo(f"[ERROR] routine_idの形式が不正です: {routine_id}", err=True)
        sys.exit(1)

    service, protocol = _connect(ctx)
    try:
        result = service.routine_control(subfunction=subfn_int, routine_id=routine_id_int)
    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)
    finally:
        _disconnect(protocol)

    if result.success:
        status = result.routine_status_record.hex(' ').upper() if result.routine_status_record else "-"
        click.echo(f"[OK]  RoutineControl subfn={hex(subfn_int)}  ID={hex(routine_id_int)}  Status={status}")
    else:
        click.echo(f"[NRC] RoutineControl  NRC={hex(result.nrc_code)}  ({result.nrc_message})")
        sys.exit(2)


if __name__ == "__main__":
    cli()
