import streamlit as st

def rapor_kaydet(cursor, rapor_numarasi, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, cevaplar):
    try:
        cursor.execute(
            "INSERT INTO raporlar (rapor_turu, report_number) VALUES (?, ?)",
            (rapor_turu, rapor_numarasi)
        )
        tablo = "voluntary_reports" if rapor_turu == "Voluntary" else "hazard_reports"
        cursor.execute(
            f"""INSERT INTO {tablo} 
                (report_number, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, ozel_cevaplar) 
                VALUES (?, ?, ?, ?, ?, ?)""",
            (rapor_numarasi, rapor_turu, rapor_konusu, olay_tarihi, veri_giris_tarihi, str(cevaplar))
        )
        return True
    except Exception as e:
        if "UNIQUE constraint failed: raporlar.report_number" in str(e):
            st.warning(f"⚠️ '{rapor_numarasi}' numaralı bir rapor zaten kayıtlı. Lütfen farklı bir numara giriniz.")
        else:
            st.error(f"❌ Hata oluştu: {e}")
        return False