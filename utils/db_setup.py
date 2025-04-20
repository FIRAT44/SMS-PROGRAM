import sqlite3

def initialize_database(db_path="sms_database.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 'raporlar' tablosunu oluştur
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raporlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rapor_turu TEXT,
            tarih_saat TEXT,
            risk_seviyesi TEXT,
            detay TEXT
        )
    """)

    # 'hazard_reports' tablosunu oluştur
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hazard_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT,
            gelen_birim TEXT,
            tarih_saat TEXT,
            olay_yeri TEXT,
            ucak_tipi TEXT,
            tescil_isareti TEXT,
            olay_daha_once_raporlanmis TEXT,
            ucus_evresi TEXT,
            olay_detayi TEXT,
            muhtemel_sebep TEXT,
            oneriler TEXT,
            degerlendirme_durumu TEXT,
            sonuclanma_durumu TEXT,
            geri_bildirim_durumu TEXT,
            atama_durumu TEXT
        )
    """)

    conn.commit()
    conn.close()
