"""验证文件保护、模型身份、退出状态和真实 stdio 协议；无需 COMSOL 许可。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import comsol_bridge as bridge
import comsol_mcp as mcp
from package_skill import inventory


def archive(path, solution=False):
    with ZipFile(path, "w") as stream:
        stream.writestr("fileversion", "2092:COMSOL 6.4.0.293")
        stream.writestr("dmodel.xml", "<model/>")
        if solution:
            stream.writestr("solution1.mphbin", b"metadata-test-only")


class FakeModel:
    def __init__(self, path, tag="ModelA"):
        self.path, self.model_tag = str(path), tag
        self.values = {}
        self.saves = 0

    def getFilePath(self): return self.path
    def tag(self): return self.model_tag
    def param(self): return self
    def set(self, key, value): self.values[key] = value
    def get(self, key): return self.values[key]
    def save(self, path):
        self.saves += 1
        archive(path)
        self.path = path


class FakeJava:
    def __init__(self, models): self.models = models
    def tags(self): return list(self.models)
    def model(self, tag): return self.models[tag]
    def uniquetag(self, prefix): return prefix + "1"
    def load(self, tag, path):
        self.models[tag] = FakeModel(path, tag)
        return self.models[tag]


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def session(self, models):
        session = bridge.ComsolSession()
        session.host, session.port = "localhost", 2036
        session.client = SimpleNamespace(java=FakeJava(models))
        return session

    def test_solution_presence_does_not_claim_validation(self):
        target = self.work / "saved.mph"
        archive(target, True)
        original = target.read_bytes()
        info = bridge.inspect_mph(str(target))
        self.assertTrue(info["solution_data_present"])
        self.assertFalse(info["solution_validated"])
        self.assertEqual(original, target.read_bytes())

    def test_corrupt_archive_is_error(self):
        target = self.work / "bad.mph"
        target.write_bytes(b"not a model")
        with self.assertRaises(ValueError): bridge.inspect_mph(str(target))

    def test_file_lock_blocks_another_process(self):
        target = self.work / "locked.mph"
        code = "import sys; sys.path.insert(0,sys.argv[1]); from pathlib import Path; from comsol_bridge import model_lock;\nwith model_lock(Path(sys.argv[2])): pass"
        with bridge.model_lock(target):
            child = subprocess.run([sys.executable, "-c", code, str(ROOT / "scripts"), str(target)],
                                   capture_output=True)
            self.assertNotEqual(child.returncode, 0)
        with bridge.model_lock(target): pass

    def test_tag_file_conflict_is_rejected(self):
        target = self.work / "wanted.mph"; archive(target)
        model = FakeModel(self.work / "different.mph")
        session = self.session({"ModelA": model})
        with self.assertRaises(ValueError): session.bind_file(str(target), "ModelA")
        self.assertIsNone(session.model)

    def test_existing_file_reuses_same_java_object(self):
        target = self.work / "wanted.mph"; archive(target)
        model = FakeModel(target)
        session = self.session({"ModelA": model})
        session.bind_file(str(target))
        self.assertIs(session.model, model)
        self.assertEqual(len(session.client.java.models), 1)

    def test_new_file_binding_is_raw_java_model_and_honors_tag(self):
        target = self.work / "new.mph"; archive(target)
        session = self.session({})
        session.bind_file(str(target), "ExplicitTag")
        self.assertEqual(session.model_tag, "ExplicitTag")
        self.assertEqual(session.set_parameters({"L": "10[mm]"}), {"L": "10[mm]"})

    def test_same_file_different_tag_does_not_duplicate(self):
        target = self.work / "wanted.mph"; archive(target)
        session = self.session({"ModelA": FakeModel(target)})
        with self.assertRaises(ValueError): session.bind_file(str(target), "OtherTag")
        self.assertEqual(len(session.client.java.models), 1)

    def test_connected_server_cannot_be_relabelled(self):
        session = self.session({})
        with self.assertRaises(RuntimeError): session.connect("localhost", 9999)
        self.assertEqual(session.port, 2036)

    def test_save_requires_new_destination_by_default(self):
        target = self.work / "original.mph"; archive(target)
        model = FakeModel(target)
        session = self.session({"ModelA": model}); session.model = model
        original = target.read_bytes()
        with self.assertRaises(FileExistsError): session.save(str(target))
        self.assertEqual(model.saves, 0)
        self.assertEqual(target.read_bytes(), original)
        saved = session.save(str(self.work / "copy.mph"))
        self.assertTrue(saved["archive"]["has_model_tree"])

    def test_failed_compilation_never_returns_old_class(self):
        source = self.work / "Probe.java"; source.write_text("class Probe {}")
        stale = source.with_suffix(".class"); stale.write_bytes(b"old-class")
        with patch.object(bridge, "discover_install", return_value={"compile": "unused"}), \
             patch.object(bridge.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout=b"", stderr=b"failed")):
            result = bridge.compile_java(str(source), str(self.work / "builds"))
        self.assertFalse(result["ok"])
        self.assertIsNone(result["class_file"])
        self.assertEqual(stale.read_bytes(), b"old-class")

    def test_zero_compile_exit_without_class_is_not_success(self):
        source = self.work / "Probe.java"; source.write_text("class Probe {}")
        with patch.object(bridge, "discover_install", return_value={"compile": "unused"}), \
             patch.object(bridge.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"", stderr=b"")):
            self.assertFalse(bridge.compile_java(str(source), str(self.work / "builds"))["ok"])

    def test_batch_outputs_are_unique_and_never_input(self):
        source = self.work / "input.mph"; archive(source)
        original = source.read_bytes()
        with patch.object(bridge, "discover_install", return_value={"batch": "unused"}), \
             patch.object(bridge.subprocess, "Popen"):
            first = bridge.run_batch(str(source), str(self.work / "runs"), wait_seconds=0)
            second = bridge.run_batch(str(source), str(self.work / "runs"), wait_seconds=0)
        self.assertNotEqual(first["run_dir"], second["run_dir"])
        output = first["command"][first["command"].index("-outputfile") + 1]
        self.assertNotEqual(str(source), output)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(first["state"], "starting")

    def test_worker_records_real_failure_exit_code(self):
        job = {"command": [sys.executable, "-c", "print('probe'); raise SystemExit(7)"],
               "stdout_log": str(self.work / "out.log"), "stderr_log": str(self.work / "err.log"),
               "batch_log": str(self.work / "batch.log"), "state": "starting"}
        path = self.work / "job.json"; path.write_text(json.dumps(job))
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/comsol_bridge.py"),
                                    "_batch-worker", str(path)], capture_output=True)
        self.assertEqual(completed.returncode, 1)
        report = bridge.job_status(str(path))
        self.assertEqual(report["returncode"], 7)
        self.assertFalse(report["process_ok"])
        self.assertIn("probe", report["stdout_log_tail"])

    def test_utf16_comsol_log(self):
        self.assertEqual(bridge.decode_log("COMSOL 日志".encode("utf-16")), "COMSOL 日志")

    def test_stdio_recovers_after_invalid_json_and_notification(self):
        requests = ["{", "[]", json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                    json.dumps({"jsonrpc": "2.0", "id": 0, "method": "ping"}),
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})]
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/comsol_mcp.py")],
                                   input="\n".join(requests) + "\n", capture_output=True,
                                   text=True, encoding="utf-8", timeout=20)
        messages = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0]["error"]["code"], -32700)
        self.assertEqual(messages[1]["error"]["code"], -32600)
        self.assertEqual(messages[2]["id"], 0)
        self.assertEqual(messages[3]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(len(messages[4]["result"]["tools"]), 11)

    def test_invalid_tool_arguments_are_protocol_error(self):
        response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "comsol_connect", "arguments": {"port": True}}})
        self.assertEqual(response["error"]["code"], -32602)

    def test_distribution_manifest_has_real_safe_files(self):
        manifest, files = inventory()
        self.assertEqual(manifest["version"], bridge.VERSION)
        self.assertGreater(len(files), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
