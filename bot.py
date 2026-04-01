import asyncio import aiohttp import os import json import hashlib import base64 from Crypto.Cipher import AES from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN") API_URL = os.getenv("API_URL")

DEVICE_ID = os.getenv("DEVICE_ID") SECRET_KEY = os.getenv("SECRET_KEY").encode() SECRET_IV = os.getenv("SECRET_IV").encode()

watch_list = [] notify_list = []

def pad(data): while len(data) % 16 != 0: data += ' ' return data

def encrypt(data): cipher = AES.new(SECRET_KEY, AES.MODE_CBC, SECRET_IV) return base64.b64encode(cipher.encrypt(pad(data).encode())).decode()

def generate_hash(data): return hashlib.sha256(data.encode()).hexdigest()

async def secure_request(session, endpoint, payload): data_json = json.dumps(payload) encrypted = encrypt(data_json) signature = generate_hash(encrypted)

body = {"data": encrypted, "hash": signature} async with session.post(f"{API_URL}/{endpoint}", json=body) as res: return await res.json() 

async def get_products(session): return await secure_request(session, "products", {"deviceId": DEVICE_ID})

async def buy_product(session, product_id, qty): return await secure_request(session, "order", { "deviceId": DEVICE_ID, "productId": product_id, "quantity": qty })

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): async with aiohttp.ClientSession() as session: products = await get_products(session)

keyboard = [] for p in products[:10]: keyboard.append([InlineKeyboardButton(p["name"], callback_data=f"menu_{p['id']}")]) await update.message.reply_text("اختر منتج:", reply_markup=InlineKeyboardMarkup(keyboard)) 

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE): text = f"📊 لوحة التحكم\n\n👀 المراقبة: {len(watch_list)}\n🔔 التنبيهات: {len(notify_list)}" keyboard = [ [InlineKeyboardButton("📦 عرض المراقبة", callback_data="show_watch")], [InlineKeyboardButton("🔔 عرض التنبيهات", callback_data="show_notify")], [InlineKeyboardButton("🧹 حذف الكل", callback_data="clear_all")] ] await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() data = query.data

if data.startswith("menu_"): pid = data.split("_")[1] keyboard = [ [InlineKeyboardButton("⚡ شراء الآن", callback_data=f"buy_{pid}")], [InlineKeyboardButton("👀 مراقبة وشراء", callback_data=f"watch_{pid}")], [InlineKeyboardButton("🔔 تنبيه فقط", callback_data=f"notify_{pid}")] ] await query.edit_message_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard)) elif data.startswith("buy_"): pid = data.split("_")[1] await query.edit_message_text("⏳ جاري الشراء...") async with aiohttp.ClientSession() as session: result = await buy_product(session, pid, 1) if result and "codes" in result: await query.message.reply_text("✅ تم:\n" + "\n".join(result["codes"])) else: await query.message.reply_text("❌ فشل") elif data.startswith("watch_"): watch_list.append({"product_id": data.split("_")[1], "chat_id": query.message.chat_id, "qty": 1}) await query.edit_message_text("✅ تمت المراقبة") elif data.startswith("notify_"): notify_list.append({"product_id": data.split("_")[1], "chat_id": query.message.chat_id}) await query.edit_message_text("🔔 سيتم التنبيه") elif data == "show_watch": await query.edit_message_text(str(watch_list) or "❌ لا يوجد") elif data == "show_notify": await query.edit_message_text(str(notify_list) or "❌ لا يوجد") elif data == "clear_all": watch_list.clear() notify_list.clear() await query.edit_message_text("🧹 تم حذف الكل") 

async def send(app, chat_id, text): await app.bot.send_message(chat_id=chat_id, text=text)

async def ultra_fast_buy(session, product_id, qty): tasks = [buy_product(session, product_id, qty) for _ in range(5)] results = await asyncio.gather(*tasks, return_exceptions=True) for r in results: if isinstance(r, dict) and "codes" in r: return r return None

async def watcher(app): async with aiohttp.ClientSession() as session: while True: products = await get_products(session)

for item in notify_list.copy(): for p in products: if str(p["id"]) == str(item["product_id"]) and p.get("available"): await send(app, item["chat_id"], f"🔔 توفر: {p['name']}") notify_list.remove(item) tasks = [] for item in watch_list.copy(): for p in products: if str(p["id"]) == str(item["product_id"]) and p.get("available"): tasks.append(process_buy(session, app, item)) if tasks: await asyncio.gather(*tasks) await asyncio.sleep(0.2) 

async def process_buy(session, app, item): result = await ultra_fast_buy(session, item["product_id"], item["qty"]) if result and "codes" in result: await send(app, item["chat_id"], "🔥 تم:\n" + "\n".join(result["codes"])) watch_list.remove(item)

async def main(): app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("panel", panel)) app.add_handler(CallbackQueryHandler(button)) for _ in range(3): asyncio.create_task(watcher(app)) await app.run_polling() 

if name == "main": asyncio.run(main())


