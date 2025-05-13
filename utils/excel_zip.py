from fpdf import FPDF
import zipfile
import tempfile
import os
from openpyxl import Workbook


def create_excel_and_zip(report_number, data_dict, ek_dosya_klasoru=None):
    # Geçici klasör oluştur
    temp_dir = tempfile.mkdtemp()
    excel_path = os.path.join(temp_dir, f"{report_number}_ozet.xlsx")

    # Excel dosyasını oluştur
    wb = Workbook()
    ws = wb.active
    ws.title = "Rapor Özeti"
    ws.append(["Bölüm", "Alan", "Değer"])

    for bolum, bilgiler in data_dict.items():
        ws.append([bolum, "", ""])  # Bölüm başlığı
        for k, v in bilgiler.items():
            v_str = str(v).replace("\n", " ").strip()
            ws.append(["", k, v_str])
        ws.append(["", "", ""])  # Bölüm arası boşluk

    wb.save(excel_path)

    # ZIP dosyasını oluştur
    zip_path = os.path.join(temp_dir, f"{report_number}_rapor.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(excel_path, arcname=f"{report_number}_ozet.xlsx")
        if ek_dosya_klasoru and os.path.exists(ek_dosya_klasoru):
            for dosya in os.listdir(ek_dosya_klasoru):
                tam_yol = os.path.join(ek_dosya_klasoru, dosya)
                zipf.write(tam_yol, arcname=f"ekler/{dosya}")

    return zip_path
