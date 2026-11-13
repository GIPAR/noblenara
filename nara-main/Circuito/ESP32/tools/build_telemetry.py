#!/usr/bin/env python3
"""Regenera interfaces usando as dependencias micro-ROS em cache e compila."""

from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys


def main():
    project = Path(__file__).resolve().parents[1]
    environment = "esp32doit-devkit-v1"
    core = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    # O build incremental roda fora do SCons, que normalmente prepara este PATH.
    compiler_bin = core / "packages/toolchain-xtensa-esp32/bin"
    os.environ["PATH"] = str(compiler_bin) + os.pathsep + os.environ.get("PATH", "")
    pio = core / "penv/bin/pio"
    library = project / ".pio/libdeps" / environment / "micro_ros_platformio"
    interface = project / "extra_packages/noblenara_interface"
    digest = hashlib.sha256()
    for path in sorted(interface.rglob("*")):
        if path.is_file() and ":Zone.Identifier" not in path.name:
            digest.update(str(path.relative_to(interface)).encode())
            digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()
    marker = library / "libmicroros/nara_interface.sha256"
    header = library / "libmicroros/include/noblenara_interface/msg/wheel_telemetry.h"
    cached = (library / "build/dev/install/setup.sh").exists()
    toolchain = library / "platformio_toolchain.cmake"

    if cached and toolchain.exists() and (
        not header.exists() or not marker.exists() or marker.read_text().strip() != fingerprint
    ):
        # Usa os fontes ja compilados: nao faz git pull nem troca suas versoes.
        sys.path.insert(0, str(library))
        from microros_utils.library_builder import Build

        builder = Build(str(library), str(interface.parent), "jazzy", str(core / "penv/bin/activate"))
        builder.check_env()
        builder.download_extra_packages()
        builder.build_mcu_environment(str(library / "metas/colcon.meta"), str(toolchain))
        builder.package_mcu_library()

    subprocess.run([str(pio), "run", "-e", environment], cwd=project, check=True)
    if not header.exists():
        raise RuntimeError("WheelTelemetry nao foi gerada; execute pio run -t clean_libmicroros e tente novamente.")
    marker.write_text(fingerprint + "\n")
    print(json.dumps({"result": "firmware compiled", "interface_sha256": fingerprint}))


if __name__ == "__main__":
    main()
