import sqlite3
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import matplotlib.pyplot as plt

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

TOKEN = os.getenv("TOKEN")

# ===== DATABASE =====
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipe TEXT,
    bank TEXT,
    kategori TEXT,
    nominal INTEGER,
    tanggal TEXT
)
""")
conn.commit()

# ===== STATES =====
MENU, BANK, KATEGORI, NOMINAL, TANGGAL, PILIH_BULAN, DELETE = range(7)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Pemasukan", "Pengeluaran"],
        ["Lihat Laporan", "Grafik"],
        ["Delete Data"]
    ]
    await update.message.reply_text(
        "📌 Pilih menu:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU

# ===== MENU =====
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Pengeluaran":
        context.user_data["tipe"] = "pengeluaran"
    elif text == "Pemasukan":
        context.user_data["tipe"] = "pemasukan"
    elif text == "Lihat Laporan":
        await update.message.reply_text("Masukkan bulan (YYYY-MM)")
        return PILIH_BULAN
    elif text == "Grafik":
        await update.message.reply_text("Masukkan bulan (YYYY-MM)")
        return PILIH_BULAN
    elif text == "Delete Data":
        cursor.execute("SELECT id, kategori, nominal FROM transaksi")
        rows = cursor.fetchall()

        if not rows:
            await update.message.reply_text("❌ Tidak ada data")
            return await start(update, context)

        text_list = "🗑 Data:\n\n"
        for r in rows:
            text_list += f"{r[0]}. {r[1]} - {r[2]}\n"

        await update.message.reply_text(text_list)
        await update.message.reply_text("Masukkan ID yang ingin dihapus:")
        return DELETE

    keyboard = [["BCA", "MANDIRI"]]
    await update.message.reply_text(
        "🏦 Pilih Bank:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return BANK

# ===== DELETE =====
async def delete_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        id_delete = int(update.message.text)
        cursor.execute("DELETE FROM transaksi WHERE id = ?", (id_delete,))
        conn.commit()

        await update.message.reply_text("✅ Data berhasil dihapus")
    except:
        await update.message.reply_text("❌ ID tidak valid")

    return await start(update, context)

# ===== BANK =====
async def pilih_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text

    if context.user_data["tipe"] == "pengeluaran":
        keyboard = [["Investasi", "Kendaraan"], ["Pribadi", "Rumah"]]
        await update.message.reply_text(
            "📂 Pilih kategori:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return KATEGORI
    else:
        context.user_data["kategori"] = "-"
        await update.message.reply_text("💰 Masukkan nominal:")
        return NOMINAL

# ===== KATEGORI =====
async def kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kategori"] = update.message.text
    await update.message.reply_text("💰 Masukkan nominal:")
    return NOMINAL

# ===== NOMINAL =====
async def nominal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["nominal"] = int(update.message.text)
    except:
        await update.message.reply_text("❌ Masukkan angka!")
        return NOMINAL

    await update.message.reply_text("📅 Masukkan tanggal (YYYY-MM-DD):")
    return TANGGAL

# ===== TANGGAL =====
async def tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tanggal"] = update.message.text

    cursor.execute("""
    INSERT INTO transaksi (tipe, bank, kategori, nominal, tanggal)
    VALUES (?, ?, ?, ?, ?)
    """, (
        context.user_data["tipe"],
        context.user_data["bank"],
        context.user_data["kategori"],
        context.user_data["nominal"],
        context.user_data["tanggal"]
    ))
    conn.commit()

    await update.message.reply_text("✅ Data berhasil disimpan!")
    return await start(update, context)

# ===== LAPORAN + GRAFIK =====
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bulan = update.message.text

    cursor.execute("""
    SELECT tipe, nominal FROM transaksi
    WHERE substr(tanggal, 1, 7) = ?
    """, (bulan,))
    
    data = cursor.fetchall()

    pemasukan = sum(d[1] for d in data if d[0] == "pemasukan")
    pengeluaran = sum(d[1] for d in data if d[0] == "pengeluaran")
    saldo = pemasukan - pengeluaran

    text = f"""
📊 LAPORAN {bulan}

💰 Pemasukan: {pemasukan}
📤 Pengeluaran: {pengeluaran}
📈 Saldo: {saldo}
"""

    await update.message.reply_text(text)

    # ===== GRAFIK =====
    x = ["Pemasukan", "Pengeluaran"]
    y = [pemasukan, pengeluaran]

    plt.figure()
    plt.bar(x, y)

    file = "grafik.png"
    plt.savefig(file)
    plt.close()

    await update.message.reply_photo(photo=open(file, "rb"))

    return await start(update, context)

# ===== RUN BOT =====
def run_bot():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_bank)],
            KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, kategori)],
            NOMINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, nominal)],
            TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tanggal)],
            PILIH_BULAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, laporan)],
            DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_data)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)

    print("🤖 Bot berjalan...")
    app.run_polling()

# ===== WEB SERVER =====
def run_web_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")

    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"🌐 Web server running on port {port}")
    server.serve_forever()

# ===== MAIN =====
if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    run_bot()
