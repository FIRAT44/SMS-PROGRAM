def yukle_sorular(db):
    sorular_ref = db.collection("sorular")
    docs = sorular_ref.stream()
    return [doc.to_dict() for doc in docs]

def soru_var_mi(db, soru_baslik):
    doc = db.collection("sorular").document(soru_baslik).get()
    return doc.exists

def soru_ekle(db, soru_dict):
    soru_id = soru_dict["soru"]
    db.collection("sorular").document(soru_id).set(soru_dict)

def guncelle_soru(db, soru_id, yeni_veri):
    db.collection("sorular").document(soru_id).update(yeni_veri)

def soru_sil(db, soru_id):
    db.collection("sorular").document(soru_id).delete()
