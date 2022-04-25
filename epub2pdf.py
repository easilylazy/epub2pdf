import re
import sys
import shutil
import zipfile
import os
import logging
from sys import platform

from tqdm import tqdm
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS, default_url_fetcher
from weasyprint.fonts import FontConfiguration


if platform == "linux" or platform == "linux2":
    # linux
    tmp_dir = "/tmp"
else:
    tmp_dir = "tmp"
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
logger = logging.getLogger("weasyprint")
logger.addHandler(logging.FileHandler(tmp_dir + "/weasyprint.log"))

def image_base_url(root_dir,opf_name):
    f = open(root_dir + opf_name, "r", encoding="utf8")
    soup = BeautifulSoup(f.read(), "lxml")
    a = soup.find("manifest")
    try:
        img_jpgs = soup.find_all("item", {"media-type": "image/jpeg"})
        for img_jpg in img_jpgs:
            try:
                if len(img_jpg.get("href").split("/")) > 1:
                    img_url = img_jpg.get("href").split("/")[0]
                    image_base = root_dir + img_url + "/"
                    return
            except Exception as e:
                print(e)

                pass
    except:
        print("no jpeg")
    try:
        img_png = a.find("item", {"media-type": "image/png"}).get("href")
        image_base = root_dir + img_png.split("/")[0] + "/"
    except:
        print("no png")
    return image_base


def get_files(root_dir, opf_name):
    ret = []
    f = open(root_dir + opf_name, "r", encoding="utf8")
    soup = BeautifulSoup(f.read(), "lxml")
    xml_files = soup.find_all("item", {"media-type": "application/xhtml+xml"})
    if xml_files is None:
        print("xml not found")
    else:
        for xml_file in xml_files:
            ret.append(xml_file.get("href"))
    return ret


def read_css(root_dir,opf_name):
    ret = []
    f = open(root_dir + opf_name, "r", encoding="utf8")
    soup = BeautifulSoup(f.read(), "lxml")
    a = soup.find("manifest")

    # css_file=a.find("item",{"media-type":"text/css"}).get("href")
    css_files = soup.find_all("item", {"media-type": "text/css"})
    if css_files is None:
        print("Css not found")
    else:
        for css_file in css_files:
            ret.append(root_dir + css_file.get("href"))
    return ret

def get_opf_name(root_dir):
    f = open(root_dir + "META-INF/" + "container.xml", "r", encoding="utf8")
    data = f.read()
    soup = BeautifulSoup(data, "html.parser")
    l = soup.find_all("rootfile")
    if len(l) == 0:
        print("no rootfile found")
        quit()
    else:
        l1 = l[0]
        pathx = l1.get("full-path")
        if "/" in pathx:
            splitx = pathx.split("/")
            root_dir = root_dir + splitx[0] + "/"
            opf_name = splitx[1]
        else:
            opf_name = pathx
    return opf_name

def writepdf(file_data,filename,root_dir,opf_name):
    font_config = FontConfiguration()
    css = read_css(root_dir,opf_name)
    image_base=  image_base_url(root_dir,opf_name)
    html = HTML(string=file_data, base_url=image_base, encoding="utf8")
    # print(css)
    html.write_pdf(filename + ".pdf", stylesheets=css, font_config=font_config)


def get_href(matched, startStr="href=", endStr="#"):
    patternStr = matched.group()
    if patternStr.find("'") != -1:
        middleStr = "'"
    elif patternStr.find('"') != -1:
        middleStr = '"'
    else:
        raise Exception("no quotation mark")
    return startStr + middleStr + endStr


def process_href_tag(data):
    startStr = "href="
    endStr = "#"
    patternStr = r'%s(["\' ]+)(.*?)%s' % (startStr, endStr)
    p = re.compile(patternStr, re.IGNORECASE)
    file_data_m = re.sub(p, get_href, data, count=0, flags=0)
    return file_data_m

def generatepdf(root_dir,opf_name):
    f = open(root_dir + "temp.xhtml", "w", encoding="utf8")
    toc_files = get_files(root_dir, opf_name)
    prev = ""
    file_cnt=len(toc_files)
    progress_bar=tqdm(range(file_cnt), desc="Generating PDF")

    for i,toc_file in zip(progress_bar,toc_files):
        progress_bar.set_description(f'{i+1}/{file_cnt}')
        if prev == toc_file:
            continue
        else:
            with open(root_dir + toc_file, "r", encoding="utf8") as xhtml_epub:
                xhtml_data = xhtml_epub.read()
                xhtml_data_m = process_href_tag(xhtml_data)
                f.write(xhtml_data_m)
        prev = toc_file

    f.close()
    


def extract_zip_to_temp(path):
    with zipfile.ZipFile(path, "r") as zip_ref:
        ret = zip_ref.extractall(tmp_dir + "/epub_temp/")


if __name__ == "__main__":
    unzip_file_path = sys.argv[1]
    filename = unzip_file_path.split("/")[-1]
    print(filename)
    file_suffix = filename.split(".")[-1]
    if file_suffix != "epub":
        print("It's a {} file".format(file_suffix))
        quit()
    shutil.copy(unzip_file_path, tmp_dir + "/epub_temp.zip")
    try:
        shutil.rmtree(tmp_dir + "/epub_temp")
    except:
        print("")
    os.mkdir(tmp_dir + "/epub_temp")
    extract_zip_to_temp(tmp_dir + "/epub_temp.zip")
    root_dir = tmp_dir + "/epub_temp/"
    # print(unzip_file_path)
    filename = filename.split(".")[0]
    opf_name=get_opf_name(root_dir)
    generatepdf(root_dir,opf_name)
    f = open(root_dir + "temp.xhtml", "r", encoding="utf8")
    writepdf(f.read(),filename,root_dir,opf_name )
    shutil.rmtree(tmp_dir + "/epub_temp")
