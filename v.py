from pyrogram import Client, filters
import random
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ganti dengan API ID dan API Hash dari my.telegram.org
api_id = '29256666'
api_hash = '2ba1bfb4019a779e43bf17e847202ecc'

# Ganti dengan API Token dari BotFather
bot_token = '7377143425:AAFUvnaiSWrHhMIjistsVVC5WEWnEDy6YoA'

# Ganti dengan ID Telegram Anda sebagai owner bot
owner_id = 6241861936  # Ganti dengan ID Telegram Anda

# Inisialisasi client bot
app = Client("jackpot_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Koneksi ke MongoDB
mongo_client = MongoClient('mongodb+srv://Kahn:bL4i1euCEnsxWuDA@cluster0yes.sr87aoe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0yes')
db = mongo_client['jackpot_db']
leaderboard_collection = db['leaderboard']

# Inisialisasi scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Fungsi untuk menambahkan koin ke pemilik bot
def add_coins_to_owner():
    owner = leaderboard_collection.find_one({"user_id": owner_id})
    if owner:
        leaderboard_collection.update_one(
            {"user_id": owner_id},
            {"$set": {"coins": 9999999}}
        )
    else:
        leaderboard_collection.insert_one({
            "user_id": owner_id,
            "username": "owner_bot",  # Ganti dengan username Anda jika ada
            "coins": 9999999
        })

# Fungsi handler untuk command /owner
@app.on_message(filters.command("owner") & filters.user(owner_id))
async def owner_command(client, message):
    logger.info(f"Received /owner command from owner_id: {owner_id}")
    
    # Tambahkan koin kepada pemilik bot
    add_coins_to_owner()
    
    # Kirim balasan
    await message.reply("Anda telah diberi 9999999 koin sebagai pemilik bot.")

# Fungsi untuk menambahkan pengguna ke leaderboard atau memperbarui skor dan koin
def update_leaderboard(user_id, username, jackpot_won=False):
    user = leaderboard_collection.find_one({"user_id": user_id})
    if user:
        if jackpot_won:
            leaderboard_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"jackpot_count": 1}}
            )
    else:
        leaderboard_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "jackpot_count": 1 if jackpot_won else 0,
            "coins": 10 if not jackpot_won else 0
        })

# Fungsi untuk mendapatkan jumlah koin pengguna
def get_coins(user_id):
    user = leaderboard_collection.find_one({"user_id": user_id})
    return user['coins'] if user else 0

# Fungsi untuk menambahkan atau mengurangi koin dari pengguna
def add_coins(user_id, coins_to_add):
    leaderboard_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": coins_to_add}},
        upsert=True
    )

# Fungsi untuk memilih emoji buah acak
def get_random_fruit_emojis():
    fruits = ["🍎", "🍌", "🍒", "🍇", "🍋", "🍊"]
    return random.choices(fruits, k=3)

# Fungsi untuk menangani perintah /jackpot
@app.on_message(filters.command("jackpot"))
async def jackpot_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or 'Anonymous'
    
    # Cek apakah pengguna memiliki cukup koin untuk bermain
    if get_coins(user_id) >= 2:
        # Kurangi 2 koin dari saldo pengguna
        add_coins(user_id, -2)
        
        # Pilih emoji buah acak
        fruit_emojis = get_random_fruit_emojis()
        fruit_display = " | ".join(fruit_emojis)
        
        # Kirim emoji buah-buahan
        await message.reply(f"🎰 {fruit_display} 🎰")
        
        # Tentukan apakah pengguna memenangkan jackpot
        if len(set(fruit_emojis)) == 1:  # Jika semua emoji sama, pengguna memenangkan jackpot
            update_leaderboard(user_id, username, True)
            await message.reply(f"🎉 Selamat {username}! Anda memenangkan JACKPOT! 🎉")
        else:
            update_leaderboard(user_id, username)
            await message.reply("Maaf, Anda tidak memenangkan jackpot kali ini.")
    else:
        await message.reply("Maaf, Anda tidak memiliki cukup koin untuk bermain. Dibutuhkan 2 koin untuk bermain.")

# Fungsi untuk menangani perintah /leaderboard
# Fungsi untuk menangani perintah /leaderboard
@app.on_message(filters.command("leaderboard"))
async def leaderboard_command(client, message):
    leaderboard = get_leaderboard()
    leaderboard_text = "Leaderboard:\n"
    for idx, user in enumerate(leaderboard, start=1):
        username = user.get('username', 'Anonymous')  # Gunakan nilai default jika username tidak ada
        leaderboard_text += f"{idx}. {username} - {user['jackpot_count']} jackpot - {user['coins']} coins\n"
    await message.reply(leaderboard_text)
# Fungsi untuk menangani perintah /coins
@app.on_message(filters.command("coins"))
async def coins_command(client, message):
    user_id = message.from_user.id
    if user_id == owner_id:  # Pemeriksaan apakah pengguna adalah pemilik bot
        user = leaderboard_collection.find_one({"user_id": user_id})
        coins = user['coins'] if user else 0
        await message.reply(f"Anda memiliki {coins} koin. Koin tidak terbatas.")
    else:
        user = leaderboard_collection.find_one({"user_id": user_id})
        coins = user['coins'] if user else 0
        await message.reply(f"Anda memiliki {coins} koin.")

# Fungsi untuk menangani perintah /transfer
@app.on_message(filters.command("transfer"))
async def transfer_command(client, message):
    if len(message.command) != 3:
        await message.reply("Format perintah tidak valid. Gunakan /transfer <user_id> <jumlah_koin>")
        return
    
    user_id = message.from_user.id
    target_user_id = int(message.command[1])
    amount = int(message.command[2])
    
    if amount <= 0:
        await message.reply("Jumlah koin yang valid harus lebih dari 0.")
        return
    
    sender_coins = get_coins(user_id)
    
    if sender_coins < amount:
        await message.reply("Maaf, Anda tidak memiliki cukup koin untuk mentransfer jumlah tersebut.")
        return
    
    add_coins(user_id, -amount)
    add_coins(target_user_id, amount)
    
    await message.reply(f"Berhasil mentransfer {amount} koin ke pengguna dengan ID {target_user_id}.")

# Fungsi untuk mendapatkan leaderboard
def get_leaderboard():
    return leaderboard_collection.find().sort("jackpot_count", -1).limit(10)

# Fungsi untuk memberikan 10 koin ke semua pengguna
def give_daily_coins():
    leaderboard_collection.update_many({}, {"$inc": {"coins": 10}})

# Jadwalkan fungsi untuk berjalan setiap hari pada pukul 12 siang
scheduler.add_job(give_daily_coins, 'cron', hour=12, timezone=pytz.timezone('Asia/Jakarta'))

# Fungsi handler untuk perintah /start
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or 'Anonymous'
    
    # Tambahkan 10 koin saat pengguna memulai bot
    add_coins(user_id, 10)
    
    # Daftar perintah dan penjelasannya
    commands_list = """
    Selamat datang di bot jackpot! Berikut adalah beberapa perintah yang dapat Anda gunakan:
    
    /start - Memulai bot dan mendapatkan 10 koin sebagai hadiah selamat datang.
    /jackpot - Bermain jackpot dengan mempertaruhkan 2 koin.
    /leaderboard - Melihat leaderboard 10 besar pemain.
    /coins - Melihat jumlah koin yang Anda miliki.
    /transfer <user_id> <jumlah_koin> - Mentransfer koin ke pengguna lain.
    """
    
    # Kirim pesan balasan beserta daftar perintah
    await message.reply(commands_list)

# Menjalankan bot
if __name__ == "__main__":
    print("Bot telah dimulai...")
    logger.info("Bot telah dimulai...")
    app.run()
