import sqlite3

def veritabani_baglanti_yap(dosya_adi="sms_database2.db"):
    return sqlite3.connect(dosya_adi, check_same_thread=False)
# Tüm SMS sistemine ait tabloları güvenli şekilde oluşturan fonksiyon
def tablolar_olustur(cursor):
    # Ana Rapor Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raporlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        rapor_turu TEXT,
        rapor_konusu TEXT,
        olay_tarihi TEXT,
        veri_giris_tarihi TEXT,
        ozel_cevaplar TEXT
    )
    """)

    # Voluntary Sistemi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voluntary_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT UNIQUE,
        rapor_turu TEXT,
        rapor_konusu TEXT,
        olay_tarihi TEXT,
        veri_giris_tarihi TEXT,
        ozel_cevaplar TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voluntary_degerlendirme (
        report_number TEXT PRIMARY KEY,
        degerlendirme_durumu TEXT,
        sonuc_durumu TEXT,
        geri_bildirim TEXT,
        atanan_kisi TEXT,
        atama_tarihi TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voluntary_ekler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        dosya_adi TEXT,
        yol TEXT,
        tarih TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Hazard Sistemi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT UNIQUE,
        rapor_turu TEXT,
        rapor_konusu TEXT,
        olay_tarihi TEXT,
        veri_giris_tarihi TEXT,
        ozel_cevaplar TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_risk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        tehlike_alani TEXT,
        tehlike_tanimi TEXT,
        riskli_olaylar TEXT,
        mevcut_onlemler TEXT,
        siddet_etkisi TEXT,
        olasilik TEXT,
        raporlanan_risk TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_onlem_coklu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT,
        risk_id INTEGER,
        onlem_aciklama TEXT,
        sorumlu TEXT,
        termin TEXT,
        gerceklesen TEXT,
        revize_risk TEXT,
        revize_siddet TEXT,
        revize_olasilik TEXT,
        etkinlik_kontrol TEXT,
        etkinlik_sonrasi TEXT,
        etkinlik_sonrasi_siddet TEXT,
        etkinlik_sonrasi_olasilik TEXT
    )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_onlem_unique
    ON hazard_onlem_coklu (report_number, risk_id)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_progress (
        report_number TEXT PRIMARY KEY,
        tamamlanan INTEGER,
        toplam INTEGER,
        yuzde INTEGER,
        eksikler TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_geri_izleme (
        report_number TEXT PRIMARY KEY,
        geri_bildirim TEXT,
        bildiren_kisi TEXT,
        komite_yorumu TEXT,
        tekrar_gz_tarihi TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hazard_kapanis (
        report_number TEXT PRIMARY KEY,
        durum TEXT,
        degerlendirme_tarihi TEXT,
        kapanis_tarihi TEXT,
        sonuc_durumu TEXT,
        atama_durumu TEXT,
        geri_bildirim_durumu TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voluntary_soru_listesi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        soru TEXT,
        tip TEXT,
        rapor_turu TEXT,
        konular TEXT,
        secenekler TEXT
    )
    """)

    # Sorular JSON sisteminden yükleniyorsa bu tablo zorunlu değil
    return True

def veritabani_temizle(cursor):
    cursor.execute("""
    DELETE FROM raporlar
    WHERE report_number NOT IN (
        SELECT report_number FROM voluntary_reports
        UNION
        SELECT report_number FROM hazard_reports
    )
    """)    