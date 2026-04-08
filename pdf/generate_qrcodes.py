import os
import qrcode

# 配置（脚本已移至 pdf/ 目录内，所以扫描当前目录）
PDF_DIR = "."
QR_DIR = os.path.join(PDF_DIR, "qr_images")
BASE_URL = "https://zmdh.jaywxl.eu.org/pdf/#"


def generate_qrcodes():
    # 如果存放二维码的文件夹不存在，则创建它
    if not os.path.exists(QR_DIR):
        os.makedirs(QR_DIR)
        print(f"创建目录: {QR_DIR}")

    pdf_files_found = 0

    # 遍历 pdf 目录下所有的文件
    for filename in os.listdir(PDF_DIR):
        if filename.lower().endswith(".pdf"):
            pdf_files_found += 1
            base_name = os.path.splitext(filename)[0]

            # 对应的二维码保存路径
            qr_filename = f"{base_name}.png"
            qr_filepath = os.path.join(QR_DIR, qr_filename)

            # 拼接云端访问链接
            url = f"{BASE_URL}{base_name}"

            # 只有当二维码不存在时才生成（避免每次都重复生成所有文件）
            if not os.path.exists(qr_filepath):
                print(f"正在生成: {base_name}.png  (链接为: {url})")

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
            else:
                print(f"已跳过: {base_name}.png (已存在)")

    if pdf_files_found == 0:
        print("没有在 pdf 目录下找到任何 PDF 文件。")


if __name__ == "__main__":
    print("-" * 40)
    print("开始生成二维码...")
    generate_qrcodes()
    print("-" * 40)
    print("生成完毕！可以直接 git commit 提交到 CF Pages 了。")
