import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Setup Log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Definisi Tahapan Percakapan
CHOOSING_TYPE, CHOOSING_BANK, CHOOSING_CATEGORY, INPUT_AMOUNT, INPUT_DATE = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [['Pengeluaran', 'Pemasukan', 'Analisis Cashflow']]
    await update.message.reply_text(
        "Halo! Pilih menu di bawah:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSING_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['tipe'] = text
    
    if text == 'Analisis Cashflow':
        # Fitur Analisis (Sederhana)
        await update.message.reply_text("Fitur analisis sedang disiapkan! Saat ini data masih disimpan sementara.")
        return ConversationHandler.END

    reply_keyboard = [['BCA', 'Mandiri']]
    await update.message.reply_text(f"Pilih Bank untuk {text}:", 
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CHOOSING_BANK

async def choose_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bank'] = update.message.text
    if context.user_data['tipe'] == 'Pengeluaran':
        reply_keyboard = [['Investasi', 'Kendaraan', 'Rumah', 'Pribadi']]
        await update.message.reply_text("Pilih kategori pengeluaran:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return CHOOSING_CATEGORY
    else:
        await update.message.reply_text("Masukkan tanggal (Format: YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
        return INPUT_DATE

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kategori'] = update.message.text
    await update.message.reply_text("Masukkan tanggal (Format: YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
    return INPUT_DATE

async def input_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tanggal'] = update.message.text
    await update.message.reply_text("Terakhir, masukkan jumlah nominalnya (angka saja):")
    return INPUT_AMOUNT

async def input_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text
    tipe = context.user_data['tipe']
    bank = context.user_data['bank']
    tgl = context.user_data['tanggal']
    
    # Di sini data seharusnya disimpan ke Database
    await update.message.reply_text(f"✅ BERHASIL DICATAT!\n\n{tipe}: Rp{amount}\nBank: {bank}\nTanggal: {tgl}")
    return ConversationHandler.END

def main():
    # Ambil Token dari Environment Variable untuk keamanan
    token = os.getenv("BOT_TOKEN")
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            CHOOSING_BANK: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_bank)],
            CHOOSING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category)],
            INPUT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_date)],
            INPUT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_amount)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
