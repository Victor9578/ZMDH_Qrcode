# -*- coding: utf-8 -*-
"""
一键处理脚本（合并自 generate_qrcodes.py / stdpdf.py / zjypdf.py）

流程：
  1. 扫描本目录（pdf/qr_images/）下的所有源 PDF
  2. 按编号生成对应二维码 PNG（缓存在 qr_pngs/ 子目录，已存在则跳过）
  3. 用二维码替换 PDF 中的原二维码，直接修改源文件
  4. 把修改后的源文件复制到上级 pdf/ 目录，命名保持为 编号.pdf

直接运行即可：python process_pdfs.py
"""

import os
import re
import shutil

import fitz  # PyMuPDF
import qrcode

# ---------------- 配置 ----------------

# 源 PDF 目录（本脚本所在目录）
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
# 最终输出目录（pdf/）
OUTPUT_DIR = os.path.normpath(os.path.join(SOURCE_DIR, ".."))
# 二维码 PNG 缓存目录
QR_DIR = os.path.join(SOURCE_DIR, "qr_pngs")

BASE_URL = "https://zmdh.jaywxl.eu.org/pdf/#"

# 参考图尺寸：标准 A4 在 300DPI 下的像素分辨率
REF_IMAGE_WIDTH = 2479
REF_IMAGE_HEIGHT = 3508

# 按文件名前缀区分替换位置（来自原 stdpdf.py / zjypdf.py）
#   stdpdf.py  => RHL 开头：右上角 (2270, 80)，尺寸 128，替换所有页
#   zjypdf.py  => SN  开头：右下区域 (2081, 2932)，尺寸 255，只替换第一页
#   all_pages: True 替换所有页，False 只替换第一页
TEMPLATE_BY_PREFIX = {
    "RHL": {"x": 2270, "y": 80, "size": 128, "all_pages": True},
    "SN": {"x": 2081, "y": 2932, "size": 255, "all_pages": False},
}
# 未匹配到前缀时使用的默认模板（默认按 SN 处理）
DEFAULT_TEMPLATE = TEMPLATE_BY_PREFIX["SN"]

# True: 即使 pdf/ 下已有同名成品也重新生成；False: 跳过已存在的成品
FORCE_OVERWRITE = False


# ---------------- 二维码生成 ----------------


def get_or_make_qr(base_name):
    """返回二维码 PNG 路径，不存在则生成。"""
    if not os.path.exists(QR_DIR):
        os.makedirs(QR_DIR)
    qr_filepath = os.path.join(QR_DIR, f"{base_name}.png")
    if os.path.exists(qr_filepath):
        return qr_filepath

    url = f"{BASE_URL}{base_name}"
    print(f"   生成二维码: {base_name}.png  (链接: {url})")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 高容错率
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_filepath)
    return qr_filepath


# ---------------- PDF 替换 ----------------


def process_pdf(pdf_path, png_path, template):
    """在 PDF 中用新二维码覆盖原二维码：直接修改源文件，再复制到 pdf/ 目录。"""
    base_name = os.path.splitext(os.path.basename(pdf_path))[0].strip()
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}.pdf")

    if not FORCE_OVERWRITE and os.path.exists(output_path):
        print(f"-> 跳过（成品已存在）: {base_name}.pdf")
        return

    doc = fitz.open(pdf_path)
    pages = doc if template["all_pages"] else [doc[0]]

    target_x, target_y, size = template["x"], template["y"], template["size"]
    scale_x = scale_y = 1.0
    for page in pages:
        pdf_w, pdf_h = page.rect.width, page.rect.height

        # 像素坐标 -> PDF 点坐标
        scale_x = pdf_w / REF_IMAGE_WIDTH
        scale_y = pdf_h / REF_IMAGE_HEIGHT
        final_x = target_x * scale_x
        final_y = target_y * scale_y
        rect = fitz.Rect(final_x, final_y, final_x + size * scale_x, final_y + size * scale_y)

        # 在目标位置附近自动吸色，取不到则默认白色底
        try:
            pix = page.get_pixmap()
            sample_x = int(final_x * (pix.width / pdf_w)) - 2
            sample_y = int(final_y * (pix.height / pdf_h)) - 2
            pixel_color = pix.pixel(max(0, sample_x), max(0, sample_y))
            fill_color = tuple(c / 255.0 for c in pixel_color[:3])
        except Exception:
            fill_color = (1.0, 1.0, 1.0)

        # 画纯色背景覆盖原二维码，再贴上新二维码
        page.draw_rect(rect, color=fill_color, fill=fill_color, overlay=True)
        page.insert_image(rect, filename=png_path)

    # 先写到临时文件，再覆盖源文件（PyMuPDF 不能原地保存正在打开的文件），
    # 最后复制到 pdf/ 目录作为成品
    tmp_path = pdf_path + ".tmp.pdf"
    doc.save(tmp_path, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp_path, pdf_path)
    shutil.copy2(pdf_path, output_path)
    print(
        f"-> 完成: {os.path.basename(pdf_path)} "
        f"(坐标 {target_x},{target_y}, 尺寸 {size}) => 已修改源文件并复制到 pdf/{base_name}.pdf"
    )


# ---------------- 主流程 ----------------


def main():
    print("-" * 40)
    print(f"源目录:   {SOURCE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("-" * 40)

    count = 0
    for filename in sorted(os.listdir(SOURCE_DIR)):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(SOURCE_DIR, filename)
        base_name = os.path.splitext(filename)[0].strip()
        # 取文件名开头的连续字母作为前缀（如 RHL2606012G2 -> RHL，SN202600642W -> SN）
        m = re.match(r"[A-Za-z]+", base_name)
        prefix = m.group(0).upper() if m else ""
        template = TEMPLATE_BY_PREFIX.get(prefix, DEFAULT_TEMPLATE)

        try:
            png_path = get_or_make_qr(base_name)
            process_pdf(pdf_path, png_path, template)
            count += 1
        except Exception as e:
            print(f"!! 文件 {filename} 处理失败: {e}")

    print("-" * 40)
    print(f"处理完毕，共 {count} 个文件。成品在 pdf/ 目录下，命名为 编号.pdf。")


if __name__ == "__main__":
    main()
