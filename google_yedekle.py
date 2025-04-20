import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

def drive_baglan():
    scope = ['https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)

def yedekle_dosya(dosya_yolu, yuklenecek_klasor_adi=None):
    drive = drive_baglan()
    dosya_adi = os.path.basename(dosya_yolu)
    gfile = drive.CreateFile({'title': dosya_adi})
    gfile.SetContentFile(dosya_yolu)
    gfile.Upload()
    print(f"✅ {dosya_adi} yüklendi.")

def toplu_yedekle():
    db_listesi = [
        "sms_database.db",
        "sms_database2.db",
        "sms_database3.db",
        "sms_occurrence.db"
    ]
    for db in db_listesi:
        if os.path.exists(db):
            yedekle_dosya(db)
        else:
            print(f"❌ {db} bulunamadı!")

if __name__ == "__main__":
    toplu_yedekle()
