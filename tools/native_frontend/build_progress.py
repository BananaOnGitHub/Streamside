"""Live owned-build output with bounded commands and persistent failure evidence."""
import codecs
import os
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import sys
import time


def command_title(args):
    if "-c" in args:
        return "Compile " + Path(args[args.index("-c") + 1]).name
    if "-o" in args:
        return "Build " + Path(args[args.index("-o") + 1]).name
    if Path(args[0]).name == "codesign":
        return "Sign or verify " + Path(args[-1]).name
    if len(args) > 2 and args[1] == "simctl":
        return "Simulator: " + args[2]
    return " ".join(str(a) for a in args[:2])


def run_logged(args, *, cwd, log_path, timeout=240, label=None, summary=False,
               group=True, heartbeat=True):
    """Stream combined output immediately, retaining the command's return text.

    Call only with owned compiler/test commands: no environment or credentials
    are dumped. A quiet command emits elapsed status every 30 seconds.
    """
    title = label or command_title(args)
    started = last_output = last_heartbeat = time.monotonic()
    chunks = []
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    process = None
    status = "FAIL"
    with Path(log_path).open("a", encoding="utf-8") as log:
        def emit(text):
            sys.stdout.write(text); sys.stdout.flush()
            log.write(text); log.flush()
        if group: print("::group::" + title, flush=True)
        emit("START: " + title + "\n$ " + shlex.join(args) + "\n")
        try:
            process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map() or process.poll() is None:
                    now = time.monotonic()
                    if now - started >= timeout:
                        raise RuntimeError(f"Command timed out after {timeout}s: {title}")
                    for key, _ in selector.select(min(0.5, timeout - (now - started))):
                        data = os.read(key.fd, 65536)
                        if data:
                            chunks.append(data); emit(decoder.decode(data))
                            last_output = time.monotonic()
                        else: selector.unregister(key.fileobj)
                    if not selector.get_map() and process.poll() is None:
                        time.sleep(0.05)
                    now = time.monotonic()
                    if heartbeat and now - max(last_output, last_heartbeat) >= 30:
                        emit(f"Still running: {title} ({now - started:.0f}s elapsed; waiting for command output)\n")
                        last_heartbeat = now
            emit(decoder.decode(b"", final=True))
            code = process.wait()
            if code:
                raise RuntimeError(f"Command exited {code}: {title}; see streamed output and build.log")
            status = "PASS"
            return b"".join(chunks).decode("utf-8", errors="replace").strip()
        except BaseException as error:
            if process is not None:
                # Kill the owned process group, including compiler/test children.
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait()
            emit("\nFAIL: " + str(error) + "\n")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print("::error title=" + title + "::Command failed; inspect this group's live output and build.log", flush=True)
            raise
        finally:
            if process is not None: process.stdout.close()
            elapsed = time.monotonic() - started
            emit(f"\n{status}: {title} ({elapsed:.1f}s)\n")
            if group: print("::endgroup::", flush=True)
            if summary and os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as report:
                    report.write(f"- **{status}** {title} — {elapsed:.1f}s\n")
