import os

def collect_all_py_files():
    # 需要扫描的文件夹
    target_files = []
    # 递归查找所有 .py 文件，排除不需要的文件夹
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        for file in files:
            if file.endswith(".py") and file != "collect_code.py":
                target_files.append(os.path.join(root, file))

    with open("all_code.txt", "w", encoding="utf-8") as outfile:
        for file_path in target_files:
            outfile.write(f"\n{'='*20}\n")
            outfile.write(f"FILE: {file_path}\n")
            outfile.write(f"{'='*20}\n\n")
            with open(file_path, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
            outfile.write("\n")

    print("✅ 汇总完毕！所有代码已存入 all_code.txt")

if __name__ == "__main__":
    collect_all_py_files()