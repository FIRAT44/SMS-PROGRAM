from utils.auth import goster_oturum_paneli
import streamlit as st
from datetime import datetime, timezone
import uuid
from utils.firebase_db import db

goster_oturum_paneli()

# Sayfa ayarları
st.set_page_config(page_title="🔍 SMS İç Denetim", layout="wide")
st.title("🔍 SMS İç Denetim")

tabs = st.tabs(["Planlama", "Denetim Kayıt", "Bulgular", "Takip & Rapor"])

# --- 1. Denetim Planlama ---
# --- 1. Denetim Planlama ---
with tabs[0]:
    st.header("📆 Denetim Planlama")
    with st.form("plan_form", clear_on_submit=True):
        plan_name = st.text_input("Denetim Adı", "Yıllık SMS İç Denetimi")
        frequency = st.selectbox("Frekans", ["Yıllık", "Çeyrek", "Aylık"])
        next_date = st.date_input("Sonraki Denetim Tarihi", datetime.today())
        elements = st.multiselect(
            "Denetim Kapsamı (SMS Bileşenleri)",
            ["Emniyet Politikası", "Risk Yönetimi", "Emniyet Güvencesi", "Emniyeti Teşvik"]
        )
        submitted = st.form_submit_button("Planı Kaydet")
        if submitted:
            # Yıla göre sıralı kod üretimi: SMS-2025-01, SMS-2025-02, ...
            year = next_date.year
            # Tüm planları çek ve aynı yıla ait olanları say
            existing = db.collection("sms_audit_plans").stream()
            count = sum(1 for p in existing if p.to_dict().get("next_date", "").startswith(str(year)))
            seq = count + 1
            plan_code = f"SMS-{year}-{seq:02d}"

            plan_id = str(uuid.uuid4())
            db.collection("sms_audit_plans").document(plan_id).set({
                "plan_code": plan_code,
                "plan_name": plan_name,
                "frequency": frequency,
                "next_date": next_date.strftime("%Y-%m-%d"),
                "elements": elements,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            st.success(f"Yeni denetim planı oluşturuldu: {plan_code} - {plan_name}")

    st.markdown("---")
    # Planları listeleme
    plans = db.collection("sms_audit_plans").stream()
    plan_list = []
    for p in plans:
        data = p.to_dict()
        data["id"] = p.id
        plan_list.append(data)
    if plan_list:
        # Tabloya kod sütunu ekle
        st.table([
            {"Kod": p.get("plan_code", ""), "Ad": p["plan_name"], "Frekans": p["frequency"], "Son Tarih": p["next_date"]}
            for p in plan_list
        ])

with tabs[1]:
    st.header("📝 Denetim Kayıt")
    # Plan seçimi
    plans = db.collection("sms_audit_plans").stream()
    plan_list = []
    for p in plans:
        data = p.to_dict()
        data["id"] = p.id
        plan_list.append(data)
    plan_options = {f"{p.get('plan_code','')} - {p['plan_name']}": p for p in plan_list}
    selected_plan = st.selectbox("Plan Seçin", list(plan_options.keys()))
    if selected_plan:
        plan = plan_options[selected_plan]

        # Yeni denetim kaydı formu
        with st.form("audit_record_form", clear_on_submit=True):
            audit_date = st.date_input("Denetim Tarihi", datetime.today())
            auditor = st.text_input("Denetçi Adı")
            observations = st.text_area("Genel Gözlemler")
            submit_audit = st.form_submit_button("Denetimi Kaydet")
            if submit_audit:
                record_id = str(uuid.uuid4())
                db.collection("sms_audit_records").document(record_id).set({
                    "plan_id": plan["id"],
                    "audit_date": audit_date.strftime("%Y-%m-%d"),
                    "auditor": auditor,
                    "observations": observations,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                st.success("Denetim kaydı oluşturuldu.")

        st.markdown("---")
        st.subheader("📋 Mevcut Denetimler")
        # Mevcut kayıtları çek
        records = db.collection("sms_audit_records").where("plan_id", "==", plan["id"]).stream()
        rec_list = [{**r.to_dict(), "id": r.id} for r in records]
        if rec_list:
            df = [
                {"Kod": plan.get("plan_code", ""), "Tarih": r["audit_date"], "Denetçi": r["auditor"]}
                for r in rec_list
            ]
            st.table(df)

            # Seçim ve Güncelleme
            selection = st.selectbox(
                "İşlem Yapılacak Kayıt",
                [f"{plan.get('plan_code')} - {r['audit_date']}" for r in rec_list]
            )
            sel_rec = next(r for r in rec_list if f"{plan.get('plan_code')} - {r['audit_date']}" == selection)
            with st.form("update_record_form"):
                u_date = st.date_input("Denetim Tarihi", datetime.fromisoformat(sel_rec["audit_date"]))
                u_auditor = st.text_input("Denetçi Adı", sel_rec["auditor"])
                u_obs = st.text_area("Genel Gözlemler", sel_rec.get("observations", ""))
                update_btn = st.form_submit_button("Güncelle")
                if update_btn:
                    db.collection("sms_audit_records").document(sel_rec["id"]).update({
                        "audit_date": u_date.strftime("%Y-%m-%d"),
                        "auditor": u_auditor,
                        "observations": u_obs,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    st.success("Denetim kaydı güncellendi.")

            # Silme butonu
            if st.button("Seçili Kaydı Sil"):
                db.collection("sms_audit_records").document(sel_rec["id"]).delete()
                st.success("Denetim kaydı silindi.")
        else:
            st.info("Henüz denetim kaydı bulunmuyor.")

# --- 3. Bulgular ---
# --- 3. Bulgular ve Uygunsuzluklar ---
with tabs[2]:
    st.header("⚠️ Bulgular ve Uygunsuzluklar")
    plan_map = {p.id: p.to_dict().get('plan_code') for p in db.collection("sms_audit_plans").stream()}
    recs = list(db.collection("sms_audit_records").stream())
    rec_list = [{**r.to_dict(), 'id': r.id} for r in recs]
    if rec_list:
        code_map = {plan_map[r['plan_id']]: r for r in rec_list}
        sel_code = st.selectbox("Denetim Kaydı Seçin", list(code_map.keys()))
        rec = code_map[sel_code]
        # Yeni bulgu ekleme
        if st.checkbox("Bu denetimde bulgu ekle/kontrol et", key=f"chk_{sel_code}"):
            existing_finds = list(db.collection("sms_audit_findings").where("record_code", "==", sel_code).stream())
            seq = len(existing_finds) + 1
            find_code = f"{sel_code}-{seq:02d}"
            st.markdown(f"**Yeni Bulgu Kodu:** {find_code}")
            with st.form(f"find_form_{sel_code}", clear_on_submit=True):
                title = st.text_input("Buluş Başlığı")
                severity = st.selectbox("Ciddiyet", ["Minor", "Major"])
                description = st.text_area("Açıklama")
                corrective = st.text_area("Düzeltici Faaliyet")
                if st.form_submit_button("Kaydet"):
                    fid = str(uuid.uuid4())
                    db.collection("sms_audit_findings").document(fid).set({
                        "finding_code": find_code,
                        "record_code": sel_code,
                        "record_id": rec['id'],
                        "title": title,
                        "severity": severity,
                        "description": description,
                        "corrective_action": corrective,
                        "status": "Açık",
                        "created_at": datetime.utcnow().isoformat()
                    })
                    st.success("Bulgu kaydedildi.")

        st.markdown("---")
        # Bulguları listele, düzenle ve sil
        finds = list(db.collection("sms_audit_findings").where("record_code", "==", sel_code).stream())
        find_list = [{**f.to_dict(), 'id': f.id} for f in finds]
        if find_list:
            st.subheader("Mevcut Bulgular")
            st.table([
                {"Kod": f['finding_code'], "Başlık": f['title'], "Durum": f['status']}
                for f in find_list
            ])
            edit_code = st.selectbox("Düzenlenecek Bulgu", [f['finding_code'] for f in find_list], key=f"edit_{sel_code}")
            sel_find = next(f for f in find_list if f['finding_code'] == edit_code)
            with st.form(f"edit_form_{edit_code}", clear_on_submit=True):
                e_title = st.text_input("Buluş Başlığı", sel_find['title'])
                e_severity = st.selectbox("Ciddiyet", ["Minor", "Major"], index=["Minor", "Major"].index(sel_find['severity']))
                e_description = st.text_area("Açıklama", sel_find['description'])
                e_corrective = st.text_area("Düzeltici Faaliyet", sel_find['corrective_action'])
                st.markdown(f"**Bulgu Kodu:** {sel_find['finding_code']}")
                if st.form_submit_button("Güncelle"):
                    db.collection("sms_audit_findings").document(sel_find['id']).update({
                        "title": e_title,
                        "severity": e_severity,
                        "description": e_description,
                        "corrective_action": e_corrective,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    st.success("Bulgu güncellendi.")
            if st.button("Bulgu Sil", key=f"del_{edit_code}"):
                db.collection("sms_audit_findings").document(sel_find['id']).delete()
                st.success("Bulgu silindi.")
        else:
            st.info("Henüz bulgu bulunmuyor.")
    else:
        st.info("Önce denetim kaydı oluşturun.")



# --- 4. Takip & Rapor ---
with tabs[3]:
    st.header("📈 Takip & Rapor")
    findings = db.collection("sms_audit_findings").stream()
    find_list = [{**f.to_dict(), "id": f.id} for f in findings]
    df = []
    for f in find_list:
        df.append({
            "ID": f["id"],
            "Başlık": f["title"],
            "Ciddiyet": f["severity"],
            "Durum": f["status"],
            "Oluşturulma": f["created_at"]
        })
    if df:
        st.dataframe(df)
        sel_find = st.selectbox("Buluş Seçin", [d["ID"] for d in df])
        sel_data = next(item for item in find_list if item["id"] == sel_find)
        new_status = st.selectbox("Durum Güncelle", ["Açık", "İşlemde", "Kapandı"])
        if st.button("Güncelle"):
            db.collection("sms_audit_findings").document(sel_find).update({
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            st.success("Durum güncellendi.")

    # SPI - Tamamlama Oranı
    total = len(find_list)
    closed = len([f for f in find_list if f["status"] == "Kapandı"] )
    rate = int((closed/total)*100) if total else 0
    st.metric("Kapalı Bulgular Oranı", f"{rate}%", delta=f"{closed}/{total}")
