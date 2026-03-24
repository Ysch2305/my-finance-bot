import sqlite3
import os
import asyncio
import matplotlib.pyplot as plt

from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ================= DATABASE =================
conn = sqlite3.connect("finance.db", check_same_thread=False)
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

# ================= STATE =================
MENU, PILIH_BANK, PILIH_KATEGORI, INPUT_NOMINAL, INPUT_TANGGAL, LAPORAN, GRAFIK = range(7)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Pemasukan", "Pengeluaran"], ["Lihat Laporan", "Grafik"]]
    await update.message.reply_text(
        "📌 Pilih menu:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MENU

# ================= MENU =================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Pemasukan":
        context.user_data["tipe"] = "pemasukan"
    elif text == "Pengeluaran":
        context.user_data["tipe"] = "pengeluaran"
    elif text == "Lihat Laporan":
        await update.message.reply_text("Masukkan bulan (YYYY-MM)")
        return LAPORAN
    elif text == "Grafik":
        await update.message.reply_text("Masukkan bulan (YYYY-MM)")
        return GRAFIK
    else:
        return MENU

    keyboard = [["BCA", "MANDIRI"]]
    await update.message.reply_text(
        "Pilih Bank:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return PILIH_BANK

# ================= PILIH BANK =================
async def pilih_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bank"] = update.message.text

    if context.user_data["tipe"] == "pengeluaran":
        keyboard = [["Investasi", "Kendaraan"], ["Pribadi", "Rumah"]]
        await update.message.reply_text(
            "Pilih Kategori:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return PILIH_KATEGORI
    else:
        context.user_data["kategori"] = "-"
        await update.message.reply_text("Masukkan nominal:")
        return INPUT_NOMINAL

# ================= PILIH KATEGORI =================
async def pilih_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kategori"] = update.message.text
    await update.message.reply_text("Masukkan nominal:")
    return INPUT_NOMINAL

# ================= INPUT NOMINAL =================
async def input_nominal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["nominal"] = int(update.message.text)
        await update.message.reply_text("Masukkan tanggal (YYYY-MM-DD):")
        return INPUT_TANGGAL
    except:
        await update.message.reply_text("❌ Masukkan angka yang benar!")
        return INPUT_NOMINAL

# ================= INPUT TANGGAL =================
async def input_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tanggal"] = update.message.text

    data = context.user_data

    cursor.execute("""
    INSERT INTO transaksi (tipe, bank, kategori, nominal, tanggal)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data["tipe"],
        data["bank"],
        data["kategori"],
        data["nominal"],
        data["tanggal"]
    ))
    conn.commit()

    await update.message.reply_text("✅ Data berhasil disimpan!")
    return await start(update, context)

# ================= LAPORAN =================
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bulan = update.message.text

    cursor.execute("""
    SELECT id, tipe, bank, kategori, nominal, tanggal
    FROM transaksi
    WHERE substr(tanggal, 1, 7) = ?
    ORDER BY tanggal ASC
    """, (bulan,))

    data = cursor.fetchall()

    pemasukan = 0
    pengeluaran = 0
    detail = ""

    for d in data:
        id_trx, tipe, bank, kategori, nominal, tanggal = d

        if tipe == "pemasukan":
            pemasukan += nominal
        else:
            pengeluaran += nominal

        detail += f"""
ID: {id_trx}
{tipe.upper()} | {bank}
Kategori: {kategori}
Nominal: {nominal}
Tanggal: {tanggal}
-------------------
"""

    saldo = pemasukan - pengeluaran

    if not data:
        detail = "Tidak ada transaksi."

    text = f"""
📊 LAPORAN BULAN {bulan}

💰 Pemasukan: {pemasukan}
📤 Pengeluaran: {pengeluaran}
📈 Saldo: {saldo}

📋 Detail:
{detail}
"""

    if saldo < 0:
        text += "\n⚠️ Arus kas BURUK!"
    elif pengeluaran > pemasukan * 0.8:
        text += "\n⚠️ Pengeluaran tinggi!"
    else:
        text += "\n✅ Arus kas sehat."

    await update.message.reply_text(text)
    return await start(update, context)

# ================= GRAFIK =================
async def grafik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bulan = update.message.text

    cursor.execute("""
    SELECT tipe, nominal
    FROM transaksi
    WHERE substr(tanggal, 1, 7) = ?
    """, (bulan,))

    data = cursor.fetchall()

    if not data:
        await update.message.reply_text("❌ Tidak ada data.")
        return await start(update, context)

    pemasukan = sum(n for t, n in data if t == "pemasukan")
    pengeluaran = sum(n for t, n in data if t == "pengeluaran")

    plt.figure()
    plt.bar(["Pemasukan", "Pengeluaran"], [pemasukan, pengeluaran])
    plt.title(f"Grafik {bulan}")

    file_name = f"grafik_{bulan}.png"
    plt.savefig(file_name)
    plt.close()

    await update.message.reply_photo(photo=open(file_name, "rb"))
    return await start(update, context)

# ================= DELETE =================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        id_trx = int(context.args[0])
        cursor.execute("DELETE FROM transaksi WHERE id = ?", (id_trx,))
        conn.commit()

        await update.message.reply_text(f"✅ ID {id_trx} dihapus!")
    except:
        await update.message.reply_text("❌ Gunakan: /delete ID")

# ================= MAIN =================
async def main():
    TOKEN = os.getenv("TOKEN")

    # 🔥 RESET TELEGRAM SESSION (WAJIB)
    bot = Bot(token=TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            PILIH_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_bank)],
            PILIH_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_kategori)],
            INPUT_NOMINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nominal)],
            INPUT_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_tanggal)],
            LAPORAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, laporan)],
            GRAFIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, grafik)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("delete", delete))

    print("🤖 Bot berjalan...")
    await app.run_polling(drop_pending_updates=True)

# ================= RUN =================
if __name__ == "__main__":
    asyncio.run(main())
