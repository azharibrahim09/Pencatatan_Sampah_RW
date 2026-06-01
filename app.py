from flask import Flask, render_template, request, redirect, url_for, flash
import json
from datetime import date

app = Flask(__name__)
app.secret_key = "banksampah_rw_secret"

DB_WARGA = "database/data_warga.json"
DB_HARGA = "database/harga_sampah.json"

def baca_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def tulis_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── WARGA: Cek Saldo ──────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    warga_ditemukan = None
    if request.method == "POST":
        id_cari = request.form.get("id_warga", "").strip()
        db = baca_json(DB_WARGA)
        warga_ditemukan = next(
            (w for w in db["warga"] if w["id"].lower() == id_cari.lower()), None
        )
        if not warga_ditemukan:
            flash("ID Warga tidak ditemukan.", "error")
    return render_template("warga_view.html", warga=warga_ditemukan)
# ── ADMIN: Dashboard ──────────────────────────────────────────
@app.route("/admin")
def admin_dashboard():
    db = baca_json(DB_WARGA)
    harga_db = baca_json(DB_HARGA)
    total_saldo = sum(w["saldo"] for w in db["warga"])
    total_transaksi = sum(len(w["riwayat_setoran"]) for w in db["warga"])
    return render_template(
        "admin_dashboard.html",
        warga_list=db["warga"],
        harga_list=harga_db["kategori"],
        total_saldo=total_saldo,
        total_transaksi=total_transaksi,
    )

# ── ADMIN: Input Setoran ──────────────────────────────────────
@app.route("/admin/setoran", methods=["POST"])
def input_setoran():
    id_warga = request.form.get("id_warga").strip().upper()
    kategori_id = request.form.get("kategori")
    berat = float(request.form.get("berat", 0))
    petugas = request.form.get("petugas", "Admin").strip()

    db_warga = baca_json(DB_WARGA)
    db_harga = baca_json(DB_HARGA)

    harga_item = next(
        (k for k in db_harga["kategori"] if k["id"] == kategori_id), None
    )
    warga = next((w for w in db_warga["warga"] if w["id"] == id_warga), None)

    if not harga_item or not warga:
        flash("ID Warga atau kategori tidak valid.", "error")
        return redirect(url_for("admin_dashboard"))

    subtotal = int(berat * harga_item["harga_per_satuan"])
    id_trx = f"TRX-{date.today().strftime('%Y%m%d')}-{len(warga['riwayat_setoran']):03d}"

    transaksi_baru = {
        "id_transaksi": id_trx,
        "tanggal": str(date.today()),
        "items": [{"kategori": kategori_id, "berat_kg": berat, "subtotal": subtotal}],
        "total": subtotal,
        "petugas": petugas,
    }
    warga["saldo"] += subtotal
    warga["riwayat_setoran"].insert(0, transaksi_baru)
    tulis_json(DB_WARGA, db_warga)

    flash(f"Setoran berhasil! +Rp {subtotal:,} untuk {warga['nama']}.", "success")
    return redirect(url_for("admin_dashboard"))

# ── ADMIN: Daftar Warga Baru ──────────────────────────────────
@app.route("/admin/warga/tambah", methods=["POST"])
def tambah_warga():
    db = baca_json(DB_WARGA)
    nomor_urut = len(db["warga"]) + 1
    warga_baru = {
        "id": f"WRG-{nomor_urut:03d}",
        "nama": request.form.get("nama").strip().title(),
        "alamat": request.form.get("alamat").strip(),
        "no_hp": request.form.get("no_hp", "").strip(),
        "tanggal_daftar": str(date.today()),
        "saldo": 0,
        "riwayat_setoran": [],
    }
    db["warga"].append(warga_baru)
    tulis_json(DB_WARGA, db)
    flash(f"Warga '{warga_baru['nama']}' berhasil didaftarkan (ID: {warga_baru['id']}).", "success")
    return redirect(url_for("admin_dashboard"))

# ── ADMIN: Update Harga ───────────────────────────────────────
@app.route("/admin/harga/update", methods=["POST"])
def update_harga():
    db = baca_json(DB_HARGA)
    for item in db["kategori"]:
        nilai_baru = request.form.get(item["id"])
        if nilai_baru:
            item["harga_per_satuan"] = int(nilai_baru)
    db["terakhir_diperbarui"] = str(date.today())
    tulis_json(DB_HARGA, db)
    flash("Harga sampah berhasil diperbarui.", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)