"""串行 MCP stdio 服务；COMSOL 运行日志不写入 JSON-RPC 通道。"""

from __future__ import annotations

from contextlib import redirect_stdout
import json
import sys

from comsol_bridge import VERSION, ComsolSession, compile_java, discover_install, inspect_mph, job_status, run_batch

SESSION = ComsolSession()
PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18")


def tool(name, description, function, properties=None, required=(), read_only=False):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties or {},
                            "required": list(required), "additionalProperties": False},
            "annotations": {"readOnlyHint": read_only}, "function": function}


STRING = {"type": "string", "minLength": 1}
TOOLS = [
    tool("comsol_discover", "发现 COMSOL 的原生程序路径，不启动求解器。", discover_install,
         {"root": STRING}, read_only=True),
    tool("comsol_inspect_mph", "离线读取 MPH 容器；不判定求解成功。", inspect_mph,
         {"path": STRING}, ("path",), True),
    tool("comsol_status", "核对当前 Server 和模型 Tag；不代表 Desktop 同步。", SESSION.status,
         read_only=True),
    tool("comsol_connect", "附着到现有 COMSOL Server，复用指定 Tag。", SESSION.connect,
         {"host": STRING, "port": {"type": "integer", "minimum": 1, "maximum": 65535},
          "model_tag": STRING}),
    tool("comsol_bind_file", "加载同机 MPH 或复用同一文件的模型；拒绝 Tag 与文件不符。", SESSION.bind_file,
         {"path": STRING, "tag": STRING}, ("path",)),
    tool("comsol_describe", "读取模型参数、组件、研究和解标签，并报告检查失败项。", SESSION.describe,
         read_only=True),
    tool("comsol_set_parameters", "写入显式全局参数并读回；不自动重建或求解。", SESSION.set_parameters,
         {"values": {"type": "object", "additionalProperties": {"type": "string"}}}, ("values",)),
    tool("comsol_save_model", "保存显式 MPH 检查点；默认拒绝覆盖已有文件。", SESSION.save,
         {"path": STRING, "overwrite": {"type": "boolean"}}, ("path",)),
    tool("comsol_compile_java", "在独立构建目录编译已审查的单文件 Java 配方。", compile_java,
         {"source": STRING, "work_dir": STRING}, ("source", "work_dir")),
    tool("comsol_run_batch", "执行已审查的 MPH/Java class，生成独立任务、日志与输出。", run_batch,
         {"input_file": STRING, "work_dir": STRING, "cores": {"type": "integer", "minimum": 1},
          "study": STRING, "wait_seconds": {"type": "number", "minimum": 0, "maximum": 60}},
         ("input_file", "work_dir")),
    tool("comsol_job_status", "读取已有任务的真实退出码、输出路径和日志尾部，不重算。", job_status,
         {"job_file": STRING}, ("job_file",), True),
]


def validate_arguments(arguments, schema):
    if not isinstance(arguments, dict):
        raise ValueError("arguments 必须是对象")
    missing = set(schema["required"]) - arguments.keys()
    extra = arguments.keys() - schema["properties"].keys()
    if missing or extra:
        raise ValueError(f"缺少字段：{sorted(missing)}；未知字段：{sorted(extra)}")
    types = {"string": (str,), "integer": (int,), "number": (int, float),
             "object": (dict,), "boolean": (bool,)}
    for name, value in arguments.items():
        spec = schema["properties"][name]
        kind = spec["type"]
        if not isinstance(value, types[kind]) or (kind in ("integer", "number") and isinstance(value, bool)):
            raise ValueError(f"{name} 类型不正确，应为 {kind}")
        if kind == "string" and not value.strip():
            raise ValueError(f"{name} 不能为空")
        if "minimum" in spec and value < spec["minimum"]:
            raise ValueError(f"{name} 小于允许值")
        if "maximum" in spec and value > spec["maximum"]:
            raise ValueError(f"{name} 大于允许值")


def rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return rpc_error(None, -32600, "Invalid Request")
    # 通知不执行有副作用的工具，也不生成响应。
    if "id" not in message:
        return None
    request_id = message["id"]
    method = message["method"]
    params = message.get("params", {})
    if not isinstance(params, dict):
        return rpc_error(request_id, -32602, "params must be an object")
    if method == "initialize":
        requested = params.get("protocolVersion")
        result = {"protocolVersion": requested if requested in PROTOCOLS else PROTOCOLS[-1],
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "comsol-agent-toolkit", "version": VERSION}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{k: v for k, v in t.items() if k != "function"} for t in TOOLS]}
    elif method == "tools/call":
        target = next((t for t in TOOLS if t["name"] == params.get("name")), None)
        if target is None:
            return rpc_error(request_id, -32602, "Unknown tool")
        arguments = params.get("arguments", {})
        try:
            validate_arguments(arguments, target["inputSchema"])
        except ValueError as exc:
            return rpc_error(request_id, -32602, str(exc))
        try:
            with redirect_stdout(sys.stderr):
                data = target["function"](**arguments)
            failed = isinstance(data, dict) and (data.get("ok") is False or data.get("process_ok") is False)
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
                      "isError": failed}
        except Exception as exc:
            result = {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
    else:
        return rpc_error(request_id, -32601, "Method not found")
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                response = handle(json.loads(line))
            except json.JSONDecodeError:
                response = rpc_error(None, -32700, "Parse error")
            except Exception as exc:
                print(f"内部错误：{type(exc).__name__}: {exc}", file=sys.stderr)
                response = rpc_error(None, -32603, "Internal error")
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
    finally:
        try:
            with redirect_stdout(sys.stderr):
                SESSION.close()
        except Exception as exc:
            print(f"断开连接失败：{exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
