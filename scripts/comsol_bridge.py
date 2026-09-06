"""COMSOL 可复用接入层；离线功能只依赖 Python 标准库。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from zipfile import BadZipFile, ZipFile

VERSION = "0.2.0"
_JVM_ATTEMPTED = False


def absolute(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def decode_log(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if data[:200].count(b"\x00") > 15:
        return data.decode("utf-16-le", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


def _version_key(value: Any) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(value)))


def discover_install(root: str | None = None) -> dict[str, Any]:
    """环境/显式目录优先；按版本检查注册表、常见目录和 PATH。"""
    candidates: list[tuple[str, Path]] = []
    if root:
        candidates.append(("argument", absolute(root)))
    for name in ("COMSOL_ROOT", "COMSOL_HOME", "COMSOL_PATH"):
        if os.environ.get(name):
            candidates.append((name, absolute(os.environ[name])))
    if os.name == "nt":
        import winreg
        registry = []
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\COMSOL", 0,
                                    winreg.KEY_READ | view) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        version = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, version) as child:
                                value = winreg.QueryValueEx(child, "COMSOLROOT")[0]
                            registry.append((version, Path(value)))
                        except OSError:
                            pass
            except OSError:
                pass
        candidates.extend(("registry", p) for _, p in sorted(
            registry, key=lambda item: _version_key(item[0]), reverse=True))
        for name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
            if os.environ.get(name):
                base = Path(os.environ[name]) / "COMSOL"
                candidates.extend(("program-files", p) for p in sorted(
                    base.glob("COMSOL*"), key=_version_key, reverse=True))
    else:
        for base in (Path("/usr/local"), Path("/opt"), Path("/Applications")):
            candidates.extend(("standard-location", p) for p in sorted(
                base.glob("[Cc][Oo][Mm][Ss][Oo][Ll]*"), key=_version_key, reverse=True))
    for value in filter(None, os.environ.get("COMSOL_SEARCH_ROOTS", "").split(os.pathsep)):
        candidates.append(("search-roots", absolute(value)))
    exe_names = {"comsol": "comsol", "server": "comsolmphserver",
                 "batch": "comsolbatch", "compile": "comsolcompile"}
    suffix = ".exe" if os.name == "nt" else ""
    seen = set()
    for source, candidate in candidates:
        candidate = candidate.parent if candidate.is_file() else candidate
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        found: dict[str, str | None] = dict.fromkeys(exe_names)
        # 只检查已知安装层级，避免遍历整个磁盘或混合不同版本的程序。
        for base in (candidate, candidate / "Multiphysics", candidate / "multiphysics"):
            for directory in (base, base / "bin", base / "bin/win64",
                              base / "bin/glnxa64", base / "bin/maci64", base / "bin/maca64"):
                for key, name in exe_names.items():
                    file = directory / (name + suffix)
                    if found[key] is None and file.is_file():
                        found[key] = str(file.resolve())
            if any(found.values()):
                return {"ok": True, "root": str(base.resolve()), "source": source, **found}
    found = {key: shutil.which(name + suffix) for key, name in exe_names.items()}
    return {"ok": any(found.values()), "root": None,
            "source": "PATH" if any(found.values()) else "not-found", **found}


def inspect_mph(path: str) -> dict[str, Any]:
    """只读容器元数据；存在 solution 条目不代表解已收敛或物理有效。"""
    file = absolute(path)
    if not file.is_file():
        raise FileNotFoundError(file)
    try:
        with ZipFile(file) as archive:
            entries = archive.infolist()
            names = {item.filename for item in entries}
            version = None
            if "fileversion" in names:
                with archive.open("fileversion") as stream:
                    version = decode_log(stream.read(4096)).strip()
            return {"path": str(file), "bytes": file.stat().st_size,
                    "fileversion": version, "entry_count": len(entries),
                    "has_model_tree": bool(names & {"dmodel.xml", "smodel.json"}),
                    "solution_data_present": any("solution" in name.lower() for name in names),
                    "solution_validated": False,
                    "entries": [{"name": e.filename, "bytes": e.file_size} for e in entries[:50]]}
    except BadZipFile as exc:
        raise ValueError(f"无法读取 MPH ZIP 容器：{file}") from exc


@contextmanager
def model_lock(path: Path):
    """仅协调采用本工具的写入者，不能锁定 COMSOL Desktop 的操作。"""
    lock = path.with_name(path.name + ".agent.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"模型已有工具锁，请核对持有进程：{lock}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "target": str(path)}, stream)
        yield
    finally:
        lock.unlink(missing_ok=True)


class ComsolSession:
    """仅附着到显式 Server；模型成员始终是原生 Java Model。"""

    def __init__(self):
        self.client = None
        self.model = None
        self.host: str | None = None
        self.port: int | None = None
        self.model_tag: str | None = None

    def connect(self, host: str = "localhost", port: int = 2036,
                model_tag: str | None = None) -> dict[str, Any]:
        global _JVM_ATTEMPTED
        if not host or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("需要有效的 Server 地址和 1–65535 端口")
        if self.client is not None:
            if (host, port) != (self.host, self.port):
                raise RuntimeError("已有连接；更换 Server 请使用独立进程，不能只改状态字段")
        else:
            with socket.create_connection((host, port), timeout=2):
                pass
            import mph
            import jpype
            if _JVM_ATTEMPTED or jpype.isJVMStarted():
                raise RuntimeError("本进程已经启动或尝试启动 JVM；请重启此工具进程后连接")
            _JVM_ATTEMPTED = True
            self.client = mph.Client(host=host, port=port)
            self.host, self.port = host, port
        tags = [str(tag) for tag in self.client.java.tags()]
        if model_tag:
            if model_tag not in tags:
                raise ValueError(f"Server 中不存在模型 Tag {model_tag!r}；现有 Tag：{tags}")
            self.model = self.client.java.model(model_tag)
            self.model_tag = model_tag
        elif self.model is None and len(tags) == 1:
            self.model_tag = tags[0]
            self.model = self.client.java.model(tags[0])
        return self.status()

    def _require_local(self):
        if self.host not in ("localhost", "127.0.0.1", "::1", socket.gethostname()):
            raise ValueError("文件绑定和保存仅支持同机 Server；远端文件须先建立明确的路径映射")

    def bind_file(self, path: str, tag: str | None = None) -> dict[str, Any]:
        if self.client is None:
            raise RuntimeError("请先连接 Server")
        self._require_local()
        target = absolute(path)
        if target.suffix.lower() != ".mph" or not target.is_file():
            raise ValueError(f"需要存在的 MPH 文件：{target}")
        tags = [str(item) for item in self.client.java.tags()]
        if tag and tag in tags:
            candidate = self.client.java.model(tag)
            existing = str(candidate.getFilePath())
            if not existing or absolute(existing) != target:
                raise ValueError(f"Tag {tag!r} 已绑定其他文件，不能当作目标模型复用")
            self.model, self.model_tag = candidate, tag
            return self.status()
        for server_tag in tags:
            candidate = self.client.java.model(server_tag)
            existing = str(candidate.getFilePath())
            if existing and absolute(existing) == target:
                if tag and tag != server_tag:
                    raise ValueError(f"文件已加载为 Tag {server_tag!r}，请使用该 Tag")
                self.model, self.model_tag = candidate, server_tag
                return self.status()
        wanted = tag or str(self.client.java.uniquetag("AgentModel"))
        # ModelUtil.load 返回 Java Model；不把 mph.Model 和 Java Model 混用。
        self.model = self.client.java.load(wanted, str(target))
        self.model_tag = str(self.model.tag())
        return self.status()

    def set_parameters(self, values: dict[str, str]) -> dict[str, str]:
        if self.model is None:
            raise RuntimeError("尚未绑定模型")
        if not values or any(not isinstance(k, str) or not k or
                             not isinstance(v, str) or not v for k, v in values.items()):
            raise ValueError("参数必须是非空名称与表达式字符串；建议表达式显式带单位")
        applied = {}
        for name, value in values.items():
            try:
                self.model.param().set(name, value)
                applied[name] = str(self.model.param().get(name))
            except Exception as exc:
                raise RuntimeError(f"参数 {name} 写入失败；此前已写入：{applied}") from exc
        return applied

    def save(self, path: str, overwrite: bool = False) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("尚未绑定模型")
        self._require_local()
        target = absolute(path)
        if target.suffix.lower() != ".mph":
            raise ValueError("检查点必须显式使用 .mph 路径")
        target.parent.mkdir(parents=True, exist_ok=True)
        with model_lock(target):
            if target.exists() and not overwrite:
                raise FileExistsError(f"默认不覆盖现存模型：{target}")
            self.model.save(str(target))
        return {"saved": str(target), "archive": inspect_mph(str(target))}

    def describe(self) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("尚未绑定模型")
        data: dict[str, Any] = {"model_tag": self.model_tag, "label": str(self.model.label())}
        failures = {}
        for name, getter in (("components", self.model.component), ("studies", self.model.study),
                             ("solutions", self.model.sol)):
            try:
                data[name] = [str(tag) for tag in getter().tags()]
            except Exception as exc:
                failures[name] = str(exc)
        try:
            data["parameters"] = {str(n): str(self.model.param().get(str(n)))
                                  for n in self.model.param().varnames()}
        except Exception as exc:
            failures["parameters"] = str(exc)
        data["inspection_errors"] = failures
        return data

    def status(self) -> dict[str, Any]:
        data = {"connected": False, "host": self.host, "port": self.port,
                "model_tag": self.model_tag, "server_tags": [], "desktop_sync_verified": False}
        if self.client is not None:
            try:
                data["server_tags"] = [str(t) for t in self.client.java.tags()]
                data["connected"] = True
                data["bound_model_present"] = self.model_tag in data["server_tags"]
            except Exception as exc:
                data["connection_error"] = str(exc)
        return data

    def close(self):
        # 不清空 Server 模型、不停止外部 Server。Server 自身的 -multi 设置仍然有效。
        if self.client is not None:
            self.client.disconnect()
            self.client = self.model = None


def compile_java(source: str, work_dir: str) -> dict[str, Any]:
    file = absolute(source)
    if file.suffix.lower() != ".java" or not file.is_file():
        raise ValueError("需要单个存在的 Java 源文件")
    executable = discover_install()["compile"]
    if not executable:
        raise RuntimeError("未发现 comsolcompile；可传入 COMSOL_ROOT")
    root = absolute(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="compile-", dir=root))
    staged = build / file.name
    shutil.copy2(file, staged)
    command = [executable, str(staged)]
    result = subprocess.run(command, cwd=build, capture_output=True, check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    stdout, stderr = decode_log(result.stdout), decode_log(result.stderr)
    (build / "compile.stdout.log").write_text(stdout, encoding="utf-8")
    (build / "compile.stderr.log").write_text(stderr, encoding="utf-8")
    class_file = staged.with_suffix(".class")
    ok = result.returncode == 0 and class_file.is_file() and class_file.stat().st_size > 0
    return {"ok": ok, "returncode": result.returncode, "command": command,
            "class_file": str(class_file) if ok else None,
            "build_dir": str(build), "stdout": stdout, "stderr": stderr}


def _write_json(path: Path, value: dict[str, Any]):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def batch_worker(job_file: str) -> int:
    path = absolute(job_file)
    job = json.loads(path.read_text(encoding="utf-8"))
    try:
        job["worker_pid"] = os.getpid()
        _write_json(path, job)
        with open(job["stdout_log"], "xb") as stdout, open(job["stderr_log"], "xb") as stderr:
            process = subprocess.Popen(job["command"], cwd=path.parent, stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            job.update(state="running", solver_pid=process.pid)
            _write_json(path, job)
            code = process.wait()
        job.update(state="finished", returncode=code, process_ok=code == 0)
        job["artifacts"] = [str(p) for p in sorted(path.parent.glob("*.mph")) if p.stat().st_size]
    except Exception as exc:
        job.update(state="failed", process_ok=False, error=f"{type(exc).__name__}: {exc}")
    job["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, job)
    return 0 if job.get("process_ok") else 1


def job_status(job_file: str) -> dict[str, Any]:
    path = absolute(job_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("stdout_log", "stderr_log", "batch_log"):
        log = Path(data[key])
        if log.is_file():
            with log.open("rb") as stream:
                prefix = stream.read(2)
                stream.seek(max(0, log.stat().st_size - 12000))
                tail = stream.read()
            if prefix in (b"\xff\xfe", b"\xfe\xff") and not tail.startswith(prefix):
                tail = prefix + tail
            data[key + "_tail"] = decode_log(tail)[-6000:]
    data["solution_validated"] = False
    return data


def run_batch(input_file: str, work_dir: str, cores: int = 2,
              study: str | None = None, wait_seconds: float = 1) -> dict[str, Any]:
    file = absolute(input_file)
    if file.suffix.lower() not in (".class", ".mph") or not file.is_file():
        raise ValueError("批处理输入必须是现存的 .class 或 .mph")
    if not isinstance(cores, int) or isinstance(cores, bool) or cores < 1 or not 0 <= wait_seconds <= 60:
        raise ValueError("cores 必须为正整数，wait_seconds 必须在 0–60 秒之间")
    executable = discover_install()["batch"]
    if not executable:
        raise RuntimeError("未发现 comsolbatch")
    root = absolute(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="batch-", dir=root))
    command = [executable, "-inputfile", str(file), "-outputfile", str(run / "result.mph"),
               "-batchlog", str(run / "batch.log"), "-np", str(cores)]
    if study:
        command.extend(["-study", study])
    job = {"schema": "comsol-agent-job/v1", "state": "starting", "command": command,
           "input": str(file), "job_file": str(run / "job.json"), "run_dir": str(run),
           "stdout_log": str(run / "stdout.log"), "stderr_log": str(run / "stderr.log"),
           "batch_log": str(run / "batch.log"), "started_at": datetime.now(timezone.utc).isoformat()}
    path = run / "job.json"
    _write_json(path, job)
    # 独立工作进程保留日志与退出码；观察超时不杀求解器，也不启动重算。
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_batch-worker", str(path)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                     start_new_session=os.name != "nt")
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        state = json.loads(path.read_text(encoding="utf-8"))["state"]
        if state in ("finished", "failed"):
            break
        time.sleep(0.1)
    return job_status(str(path))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="COMSOL Agent 工具包")
    commands = parser.add_subparsers(dest="action", required=True)
    discover = commands.add_parser("discover"); discover.add_argument("--root")
    inspect = commands.add_parser("inspect-mph"); inspect.add_argument("path")
    compile_cmd = commands.add_parser("compile"); compile_cmd.add_argument("source")
    compile_cmd.add_argument("--work-dir", required=True)
    batch = commands.add_parser("batch"); batch.add_argument("input_file")
    batch.add_argument("--work-dir", required=True); batch.add_argument("--cores", type=int, default=2)
    batch.add_argument("--study"); batch.add_argument("--wait-seconds", type=float, default=1)
    status = commands.add_parser("job-status"); status.add_argument("job_file")
    worker = commands.add_parser("_batch-worker"); worker.add_argument("job_file")
    args = vars(parser.parse_args(argv)); action = args.pop("action")
    if action == "_batch-worker":
        return batch_worker(**args)
    functions = {"discover": discover_install, "inspect-mph": inspect_mph,
                 "compile": compile_java, "batch": run_batch, "job-status": job_status}
    try:
        result = functions[action](**args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("ok") is False or result.get("process_ok") is False else 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
