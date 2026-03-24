import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)

# ===== TOKEN (AMAN) =====
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
MENU, BANK, KATEGORI, NOMINAL, TANGGAL, PILIH_BULAN = range(6)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Pemasukan", "Pengeluaran"], ["Lihat Laporan"]]
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
        await update.message.reply_text(
            "Masukkan bulan (format: YYYY-MM)\nContoh: 2026-03"
        )
        return PILIH_BULAN

    keyboard = [["BCA", "MANDIRI"]]
    await update.message.reply_text(
        "🏦 Pilih Bank:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return BANK

# ===== BANK =====
async def pilih_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text

    if context.user_data["tipe"] == "pengeluaran":
        keyboard = [
            ["Investasi", "Kendaraan"],
            ["Pribadi", "Rumah"]
        ]
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
        await update.message.reply_text("❌ Masukkan angka yang valid!")
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

# ===== LAPORAN BULANAN =====
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bulan = update.message.text  # format YYYY-MM

    cursor.execute("""
    SELECT tipe, SUM(nominal) FROM transaksi
    WHERE substr(tanggal, 1, 7) = ?
    GROUP BY tipe
    """, (bulan,))
    
    data = cursor.fetchall()

    pemasukan = 0
    pengeluaran = 0

    for d in data:
        if d[0] == "pemasukan":
            pemasukan = d[1] or 0
        elif d[0] == "pengeluaran":
            pengeluaran = d[1] or 0

    saldo = pemasukan - pengeluaran

    # ===== ANALISA =====
    if pemasukan == 0 and pengeluaran == 0:
        analisa = "⚠️ Belum ada data di bulan ini."
    elif saldo < 0:
        analisa = (
            "⚠️ Arus kas BURUK!\n"
            "Pengeluaran lebih besar dari pemasukan.\n"
            "Kemungkinan terlalu banyak spending konsumtif."
        )
    elif pengeluaran > pemasukan * 0.8:
        analisa = (
            "⚠️ Arus kas kurang sehat.\n"
            "Pengeluaran mendekati pemasukan.\n"
            "Sebaiknya mulai kontrol pengeluaran."
        )
    else:
        analisa = "✅ Arus kas BAGUS! Keuangan kamu sehat."

    text = f"""
📊 LAPORAN BULAN {bulan}

💰 Pemasukan: {pemasukan}
📤 Pengeluaran: {pengeluaran}
📈 Saldo: {saldo}

🧠 Analisa:
{analisa}
"""

    await update.message.reply_text(text)
    return await start(update, context)

# ===== MAIN =====
def main():
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
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
