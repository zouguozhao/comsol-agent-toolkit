"""按显式清单校验、打包或安装 Skill；不会遍历案例目录或覆盖同名安装。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def inventory(root=ROOT):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if len(files) != len(set(files)):
        raise ValueError("清单包含重复文件")
    result = []
    for name in files:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError(f"无效的分发路径：{name}")
        file = root / name
        if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
            raise ValueError(f"清单文件缺失或越出工具目录：{name}")
        if file.suffix.lower() in (".mph", ".class", ".pyc", ".log", ".jar", ".exe"):
            raise ValueError(f"不应分发的生成文件：{name}")
        result.append({"path": name, "bytes": file.stat().st_size,
                       "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    return manifest, result


def main():
    parser = argparse.ArgumentParser(description="COMSOL Skill 清单校验、打包和本地安装")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--zip", dest="zip_path")
    choice.add_argument("--install", help="目标 skills 父目录；同名目录存在时拒绝覆盖")
    args = parser.parse_args()
    manifest, files = inventory()
    result = {"name": manifest["name"], "version": manifest["version"], "file_count": len(files)}
    if args.zip_path:
        target = Path(args.zip_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(target, "x", compression=ZIP_DEFLATED) as archive:
            for file in files:
                archive.write(ROOT / file["path"], manifest["name"] + "/" + file["path"])
            archive.writestr(manifest["name"] + "/SHA256SUMS.json",
                             json.dumps(files, ensure_ascii=False, indent=2))
        result.update(archive=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    elif args.install:
        target = Path(args.install).expanduser().resolve() / manifest["name"]
        target.mkdir(parents=True, exist_ok=False)
        for file in files:
            destination = target / file["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / file["path"], destination)
        result["installed"] = str(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
