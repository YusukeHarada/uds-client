"""
CLIエントリポイント。

clickを使用してコマンドライン引数を宣言的に定義する。
UIロジック（引数解析・画面出力）のみを担い、
診断ロジックはDiagnosticServiceに委ねる。
"""
import sys
import click
from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol

DOIP_PORT = 13400


@click.command()
@click.option("--ip",      required=True,                    help="ECU IP address")
@click.option("--port",    default=DOIP_PORT, show_default=True, help="DoIP port")
@click.option("--did",     required=True,                    help="DID in hex (e.g. F190)")
@click.option("--log",     default="INFO",   show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
              help="Log level")
@click.option("--logfile", default="uds_log.json", show_default=True,
              help="Log output file (JSON Lines format)")
def cli(ip: str, port: int, did: str, log: str, logfile: str) -> None:
    """UDS診断ツール — DoIP / ReadDataByIdentifier (Step1)"""
    try:
        did_int = int(did, 16)
    except ValueError:
        click.echo(f"[ERROR] Invalid DID format: '{did}' (expected hex, e.g. F190)", err=True)
        sys.exit(1)

    protocol = DoIPProtocol(host=ip, port=port)

    try:
        click.echo(f"[INFO] Connecting to {ip}:{port} ...")
        protocol.connect()
    except OSError as e:
        click.echo(f"[ERROR] Connection failed: {e}", err=True)
        sys.exit(1)

    service = DiagnosticService(
        protocol=protocol,
        log_path=logfile,
        log_level=log,
    )

    try:
        result = service.read_data_by_identifier(did=did_int)
    except Exception as e:
        click.echo(f"[ERROR] Communication error: {e}", err=True)
        sys.exit(1)
    finally:
        protocol.disconnect()

    if result.success:
        click.echo(f"[OK]  DID={hex(did_int)}  Data={result.data.hex(' ').upper()}")
        sys.exit(0)
    else:
        click.echo(
            f"[NRC] DID={hex(did_int)}  "
            f"NRC={hex(result.nrc_code)}  ({result.nrc_message})"
        )
        sys.exit(2)


if __name__ == "__main__":
    cli()
