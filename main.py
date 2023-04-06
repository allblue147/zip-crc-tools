import os
import re
import zlib
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
                    help="输入crc32字符串 如: python .\main.py -t '1|0x83dcefb7, 0xd9403697| 2|0x647e170e, 0x0a6216d9| 3|0x92d786fd| 4|0xf7c0246a|'")
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
        _extracted_from_init_23("由于本项目目录没有crc32文件夹, 请查看README.txt的食用过程第一项!")
    # 3.检查输入的文件是否为zip格式
    if args.f and not args.f.endswith(".zip"):
        _extracted_from_init_23("参数-f 需要的是一个PK-zip格式的文件!")
    return file_path, save_dir


# TODO Rename this here and in `init`
def _extracted_from_init_23(arg0):
    console.print(arg0, style="bold red")
    os.system("pause")
    exit(-1)

def upper_crack(hex_crc, size):
    res = subprocess.Popen(f'python "{os.path.join(base_dir, "crc32", "crc32.py")}" reverse {hex_crc}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = res.stdout.read().decode('gbk').replace("\r\r\n", "\r\n")
    return re.findall(PATTERNS[(size - 4)], result)

def lower_crack(crc_num):
    for j in range(1, 4):
        for i in itertools.product(range(256), repeat=j):
            if crc_num == zlib.crc32(bytes(i)):
                return [bytes(i).decode("latin1")]
    return []

def crack_crc(hex_crc, size):
    plan_text = []
    if 1 <= int(size) <= 3:
        plan_text = lower_crack(int(hex_crc, 16))
    elif  4 <= int(size) <= 6:
        plan_text = upper_crack(hex_crc, int(size))
    return plan_text

def match(size, text):
    if (lis := re.findall(f"{size}\\|(.*?)\\|", text)) != []:
        return [i.strip() for i in lis[0].split(",")]
    return []

def get_size(hex_crc, size_dict: dict):
    for key, value in size_dict.items():
        for crc in value:
            if hex_crc == crc:
                return key

def get_crc(crc_str):
    size_dict = {str(i): match(i, crc_str) for i in range(1, 7)}
    crc_list = re.findall("(0x.*?)[,|]", args.t)

    zip_info = []
    for hex_crc in crc_list:
        size = get_size(hex_crc, size_dict)
        plan_text = crack_crc(hex_crc, size)
        zip_info.append(["None", size, hex_crc, plan_text])
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
            zip_info.append([file_name.encode("cp437").decode("gbk"), size, hex_crc])

    for i, (file_name, size, hex_crc) in enumerate(zip_info):
        plan_text = crack_crc(hex_crc, size)
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
        console.print("按顺序拼接在一起: [bold magenta]" + "".join(info[-1][0] for info in zip_info) + "[/]")

    if console.input("是否需要生成字典: ([bold red]y[/]/[bold green]N[/]): ") in ["Y", "y"]:
        with open(os.path.join(save_dir, "output.dic"), "w") as f:
            with tqdm(itertools.product(*[info[-1] for info in zip_info if info[-1] != []]), desc="Generate Dictionary: ") as bar:
                for i in bar:
                    f.write("".join(i) + "\n")
        print("Generate Dictionary Finish!")

    if console.input("是否需要导出txt: ([bold red]y[/]/[bold green]N[/]): ") in ["Y", "y"]:
        with open(os.path.join(save_dir, "output.txt"), "w") as f:
            f.write(", ".join(["File name", "Size", "Checksum", "Text"]) + "\n")
            for info in zip_info:
                for i in info:
                    f.write(','.join(i)) if isinstance(i, list) else f.write(f"{str(i)},")
                f.write("\n")
        print("Generate txt-file Finish!")
        time.sleep(1)
