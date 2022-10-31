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
parser.add_argument("-f", type=str, default=None, required=False,
                    help="输入PK-zip文件")
parser.add_argument("-t", type=str, default=None, required=False,
                    help="输入crc32字符串 如: python main.py -t '0xce70d424, 0x1c8600e3, ..., 0x01521186'")
args  = parser.parse_args()

console = Console()
color = Color.Color()
base_dir = os.path.dirname(os.path.abspath(__file__))
PATTERNS = ["4 bytes: (.*?) {", "5 bytes: (.*?) \(", "6 bytes: (.*?) \("]

def init():
    # 1.检查传入的参数
    file_path, save_dir = None, None
    if args.f and args.t:
        console.print("参数-f 和 参数-t只可以使用一个哦~~", style="bold red")
        exit(-1)
    elif args.f is None and args.t is None:
        console.print("参数-f 和 参数-t你总得使用一个哦~~", style="bold red")
        exit(-1)

    # 2.检查文件是否存在顺便设置sava_dir
    if args.f:
        file_path = os.path.abspath(os.path.abspath(args.f))
        if os.path.exists(file_path):
            save_dir = os.path.dirname(file_path)
        else:
            console.print("参数-f 的zip文件不存在~", style="bold red")
    elif args.t:
        save_dir = os.getcwd()
            
    # 2.检查是否有crc32项目
    if not os.path.exists(os.path.join(base_dir, "crc32")):
        console.print("由于本项目目录没有crc32文件夹, 请查看README.txt的食用过程第一项!", style="bold red")
        os.system("pause")
        exit(-1)

    # 3.检查输入的文件是否为zip格式
    if args.f and not args.f.endswith(".zip"):
        console.print("参数-f 需要的是一个PK-zip格式的文件!", style="bold red")
        os.system("pause")
        exit(-1)
    return file_path, save_dir

def get_crc(crc_str):
    zip_info = []
    crc_list = [i.strip() for i in crc_str.split(",")]
    for hex_crc in crc_list:
        res = subprocess.Popen(f"python {os.path.join(base_dir, 'crc32', 'crc32.py')} reverse {hex_crc}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = res.stdout.read().decode('gbk').replace("\r\r\n", "\r\n")
        plan_text = re.findall(PATTERNS[0], result)
        zip_info.append(["None", 4, hex_crc, plan_text])
    return zip_info

def read_zip(file_path):
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
        res = subprocess.Popen(f"python {base_dir}/crc32/crc32.py reverse {hex_crc}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    file_path, save_dir = init()
    
    if args.f:
        zip_info = read_zip(file_path)
    elif args.t:
        zip_info = get_crc(args.t)
    
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
                    f.write(','.join(i)) if isinstance(i, list) else f.write(f"{str(i)},")
                f.write("\n")
        print("Generate Csv-file Finish!")
        time.sleep(1)
