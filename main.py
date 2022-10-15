import os
import re
import time
import copy
import zipfile
import argparse
import itertools
import subprocess
from tqdm import tqdm
from rich.console import Console
from prettytable import PrettyTable

from src import Color

parser = argparse.ArgumentParser()
parser.add_argument("-f", type=str, default=None, required=True,
                    help="输入PK-zip文件")
args  = parser.parse_args()

base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.abspath(args.f)
save_dir = os.path.dirname(file_path)


console = Console()
color = Color.Color()
PATTERNS = ["4 bytes: (.*?) {", "5 bytes: (.*?) \(", "6 bytes: (.*?) \("]

if not str(args.f).endswith(".zip"):
    console.print("-f 参数需要的是一个PK-zip格式的文件!", style="bold red")
    os.system("pause")
    exit(-1)


def read_zip():
    z = zipfile.ZipFile(file_path)
    zip_info = []
    name_list = z.namelist()
    for file_name in name_list:
        if file_name.endswith(".txt"):
            info = z.getinfo(file_name)
            hex_crc = hex(info.CRC)
            size = info.file_size
            zip_info.append([file_name, size, hex_crc])

    for i, (file_name, size, hex_crc) in enumerate(zip_info):
        res = subprocess.Popen(f"python {base_dir}/crc32-master/crc32.py reverse {hex_crc}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = res.stdout.read().decode('gbk').replace("\r\r\n", "\r\n")

        plan_text = []
        if size == 4:
            plan_text = re.findall(PATTERNS[0], result)
        elif size == 5:
            plan_text = re.findall(PATTERNS[1], result)
        elif size == 6:
            plan_text = re.findall(PATTERNS[2], result)

        zip_info[i].append(plan_text)
    return zip_info


def show_table(zip_info):
    tables = copy.deepcopy(zip_info)
    for i, info in enumerate(zip_info):
        plan_text = info[-1]

        if len(plan_text) > 1:
            tables[i][-1] = color.red(plan_text[0])
            tables[i].append(color.red("True"))
        elif len(plan_text) == 1:
            tables[i][-1] = color.green(plan_text[0])
            tables[i].append("False")
        else:
            tables[i][-1] = color.red("None")
            tables[i].append(color.red("*"))

    table = PrettyTable()
    table.title = "Byxs20's Zip Crc32 Tools"
    table.field_names = ["File name", "Size", "Checksum", "Text", "More"]
    table.add_rows(tables)
    print(table)
    return tables


if __name__ == "__main__":
    zip_info = read_zip()
    tables = show_table(zip_info)

    if all(info[-1] == "False" for info in tables):
        console.print("按顺序拼接在一起: [bold magenta]" + "".join(info[-1][0] for info in zip_info) + "[/bold magenta]")

    if console.input("是否需要生成字典: ([bold red]y[/bold red]/[bold green]N[/bold green]): ") in ["Y", "y"]:
        with open(os.path.join(save_dir, "output.dic"), "w") as f:
            with tqdm(itertools.product(*[info[-1] for info in zip_info if info[-1] != []]), desc="Generate Dictionary: ") as bar:
                for i in bar:
                    f.write("".join(i) + "\n")
        print("Generate Dictionary Finish!")

    if console.input("是否需要导出csv: ([bold red]y[/bold red]/[bold green]N[/bold green]): ") in ["Y", "y"]:
        with open(os.path.join(save_dir, "output.csv"), "w") as f:
            f.write(", ".join(["File name", "Size", "Checksum", "Text"]) + "\n")
            for info in zip_info:
                for i in info:
                    f.write('   '.join(i)) if isinstance(i, list) else f.write(f"{str(i)}, ")
                f.write("\n")
        print("Generate Csv-file Finish!")
        time.sleep(1)
