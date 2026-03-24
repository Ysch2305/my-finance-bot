import os
import logging
from datetime import datetime
import matplotlib.pyplot as plt

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)

data = []

# =========================
# SET COMMAND (POPUP TELEGRAM)
# =========================
async def set_commands(app):
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("tambah_pemasukan", "Tambah pemasukan"),
        BotCommand("tambah_pengeluaran", "Tambah pengeluaran"),
        BotCommand("laporan", "Lihat laporan"),
        BotCommand("delete", "Hapus data"),
        BotCommand("grafik", "Grafik keuangan"),
    ]
    await app.bot.set_my_commands(commands)

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot siap digunakan")

# =========================
# TAMBAH PEMASUKAN
# =========================
async def tambah_pemasukan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jumlah = int(context.args[0])
        keterangan = context.args[1]
        bank = context.args[2]

        data.append({
            "tanggal": datetime.now(),
            "tipe": "pemasukan",
            "jumlah": jumlah,
            "keterangan": keterangan,
            "bank": bank
        })

        await update.message.reply_text("✅ Pemasukan ditambahkan!")
    except:
        await update.message.reply_text("❌ Format salah!")

# =========================
# TAMBAH PENGELUARAN
# =========================
async def tambah_pengeluaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jumlah = int(context.args[0])
        keterangan = context.args[1]
        bank = context.args[2]

        data.append({
            "tanggal": datetime.now(),
            "tipe": "pengeluaran",
            "jumlah": jumlah,
            "keterangan": keterangan,
            "bank": bank
        })

        await update.message.reply_text("✅ Pengeluaran ditambahkan!")
    except:
        await update.message.reply_text("❌ Format salah!")

# =========================
# LAPORAN
# =========================
async def laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data:
        await update.message.reply_text("📭 Belum ada data")
        return

    text = "📊 LAPORAN:\n\n"
    total_masuk = 0
    total_keluar = 0

    for i, item in enumerate(data):
        text += (
            f"{i}. {item['tipe']} - Rp{item['jumlah']}\n"
            f"   {item['keterangan']} ({item['bank']})\n\n"
        )

        if item["tipe"] == "pemasukan":
            total_masuk += item["jumlah"]
        else:
            total_keluar += item["jumlah"]

    saldo = total_masuk - total_keluar

    text += f"💰 Total Masuk: Rp{total_masuk}\n"
    text += f"💸 Total Keluar: Rp{total_keluar}\n"
    text += f"📌 Saldo: Rp{saldo}"

    await update.message.reply_text(text)

# =========================
# DELETE
# =========================
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        index = int(context.args[0])

        if index < 0 or index >= len(data):
            await update.message.reply_text("❌ Index tidak valid")
            return

        deleted = data.pop(index)

        await update.message.reply_text(
            f"🗑 Data dihapus:\n{deleted['keterangan']} - Rp{deleted['jumlah']}"
        )
    except:
        await update.message.reply_text("❌ Format: /delete index")

# =========================
# GRAFIK
# =========================
async def grafik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data:
        await update.message.reply_text("❌ Tidak ada data")
        return

    bulan = {}

    for item in data:
        key = item["tanggal"].strftime("%Y-%m")

        if key not in bulan:
            bulan[key] = 0

        if item["tipe"] == "pemasukan":
            bulan[key] += item["jumlah"]
        else:
            bulan[key] -= item["jumlah"]

    x = list(bulan.keys())
    y = list(bulan.values())

    plt.figure()
    plt.plot(x, y)
    plt.title("Grafik Keuangan Bulanan")

    filename = "grafik.png"
    plt.savefig(filename)
    plt.close()

    await update.message.reply_photo(photo=open(filename, "rb"))

# =========================
# MAIN
# =========================
def main():
    print("🤖 Bot berjalan...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah_pemasukan", tambah_pemasukan))
    app.add_handler(CommandHandler("tambah_pengeluaran", tambah_pengeluaran))
    app.add_handler(CommandHandler("laporan", laporan))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("grafik", grafik))

    # 🔥 SET POPUP COMMAND
    app.post_init = set_commands

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
