import sys
import os
import re
import subprocess
import tempfile


def scan_all_lib_files(interior_lib_folder: str):
    """扫描lib/interior全部*.wcn，返回[(源绝对路径, exe内部目标路径)]"""
    items = []
    if not os.path.isdir(interior_lib_folder):
        return items
    for fname in os.listdir(interior_lib_folder):
        if fname.lower().endswith(".wcn"):
            src = os.path.join(interior_lib_folder, fname)
            dst = os.path.join("lib", "interior", fname)
            items.append((src, dst))
    return items


def scan_ext_dependencies(wcn_file: str, interior_lib_folder: str) -> list[str]:
    """扫描wcn脚本中所有 ext @xxx.wcn，仅打印提示"""
    deps = set()
    ext_pattern = re.compile(r'^\s*ext\s+@([\w\.]+)', re.MULTILINE)
    with open(wcn_file, "r", encoding="utf-8") as f:
        content = f.read()
    matches = ext_pattern.findall(content)
    for lib_name in matches:
        lib_full_path = os.path.join(interior_lib_folder, lib_name)
        if os.path.exists(lib_full_path):
            deps.add(lib_full_path)
        else:
            print(f"⚠️ 警告：依赖库文件不存在 {lib_full_path}")
    return list(deps)


def main():
    if len(sys.argv) != 2:
        print("Usage: python wper.py yourfile.wcn")
        print("example: python wper.py test.wcn")
        sys.exit(1)

    wcn_file = sys.argv[1]
    wcn_abs = os.path.abspath(wcn_file)
    if not os.path.exists(wcn_abs):
        print(f"Error: file not found {wcn_abs}")
        sys.exit(1)

    work_dir = os.path.dirname(wcn_abs)
    wcn_basename = os.path.basename(wcn_abs)
    exe_name = os.path.splitext(wcn_basename)[0] + ".exe"

    script_root = os.path.dirname(os.path.abspath(__file__))
    interior_lib_folder = os.path.join(script_root, "lib", "interior")

    ext_dep_files = scan_ext_dependencies(wcn_abs, interior_lib_folder)
    all_lib_items = scan_all_lib_files(interior_lib_folder)

    print(f"🔍 扫描ext依赖，找到 {len(ext_dep_files)} 个外部wcn库：")
    for d in ext_dep_files:
        print(f"    -> {d}")
    print(f"📦 lib/interior总资源数: {len(all_lib_items)}")

    # 在系统临时目录生成启动脚本，不污染项目文件夹
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
        temp_script = tf.name
        temp_code = '''
import sys,os
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)

sys.path.insert(0, get_resource_path("."))
import wanted

target_wcn = get_resource_path("''' + wcn_basename + '''")
with open(target_wcn,"r",encoding="utf-8") as f:
    code_lines = [l for l in f.read().split('\\n') if l.strip()!='' and not l.strip().startswith('#')]
wanted.interpret(wanted.tokenize(code_lines), True)
input("Press Enter to exit...")
'''
        tf.write(temp_code)

    nuitka_args = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=force",
        "--remove-output",
        f"--output-filename={exe_name}",
        f"--include-data-files={wcn_abs}={wcn_basename}",
        temp_script
    ]

    # 逐个添加lib/interior下所有wcn资源（规避--include‑data‑dir的1392bug）
    for src_path, dst_path in all_lib_items:
        nuitka_args.append(f"--include-data-files={src_path}={dst_path}")

    print("\n===== Start Nuitka compile =====")
    print("Nuitka args:")
    for arg in nuitka_args:
        print("  ", arg)

    ret = subprocess.run(nuitka_args, cwd=work_dir)

    # 清理临时文件
    try:
        os.unlink(temp_script)
    except OSError:
        pass

    if ret.returncode == 0:
        print(f"\n✅ Build success! Output: {os.path.join(work_dir, exe_name)}")
    else:
        print("\n❌ Compile failed")
        sys.exit(ret.returncode)


if __name__ == "__main__":
    main()
