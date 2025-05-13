from firebase_admin import storage
import uuid

def yukle_ek_dosya(file, tur, rapor_no):
    blob_path = f"{tur}/{rapor_no}/{uuid.uuid4()}_{file.name}"
    blob = storage.bucket().blob(blob_path)
    blob.upload_from_file(file)
    blob.make_public()
    return blob.public_url

def listele_ek_dosyalar(tur, rapor_no):
    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix=f"{tur}/{rapor_no}/")
    return [{"adi": b.name.split("/")[-1], "url": b.public_url} for b in blobs]

def sil_ek_dosya(tur, rapor_no, dosya_adi):
    blob_path = f"{tur}/{rapor_no}/{dosya_adi}"
    blob = storage.bucket().blob(blob_path)
    blob.delete()