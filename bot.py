import os
import json
import time
import logging
import secrets
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل گفتگو
(
    GET_TOKEN,
    SELECT_WORKER,
    WORKER_PANEL,
    NEW_WORKER_NAME,
    GET_FILE,
    GET_SEC_NAME,
    GET_SEC_VAL,
    GET_KV_NAME,
    GET_D1_NAME,
) = range(9)

# ----------------- تنظیمات -----------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
UPSTASH_URL = os.getenv("UPSTASH_REST_URL", "YOUR_UPSTASH_REST_URL_HERE")
UPSTASH_TOKEN = os.getenv("UPSTASH_REST_TOKEN", "YOUR_UPSTASH_REST_TOKEN_HERE")
# -------------------------------------------

CLOUDFLARE_URL = "https://dash.cloudflare.com/profile/api-tokens"


async def db_command(command: list):
    """ارتباط ایمن و سریع با دیتابیس Upstash بدون فریز شدن ربات"""
    if not UPSTASH_URL or not UPSTASH_TOKEN or "YOUR_UPSTASH" in UPSTASH_URL:
        return None
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            res = await client.post(UPSTASH_URL, headers=headers, json=command)
            return res.json().get("result")
        except Exception:
            return None


async def track_activity(user_id: int):
    now = time.time()
    await db_command(["SADD", "bot_all_users", str(user_id)])
    await db_command(["ZADD", "bot_active_users", now, str(user_id)])


async def send_or_edit(update: Update, text: str, reply_markup=None):
    """تابع هوشمند برای جلوگیری از کرش: پیام جدید باشد Reply میکند، دکمه باشد Edit میکند"""
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        return await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    else:
        return await update.effective_message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پایدار منوی اصلی"""
    if "cf_token" in context.user_data:
        account_name = context.user_data.get("account_name", "اکانت شما")
        keyboard = [
            [InlineKeyboardButton("📁 مدیریت و لیست ورکرها", callback_data="load_workers")],
            [InlineKeyboardButton("📊 آمار کاربران ربات", callback_data="bot_stats")],
            [InlineKeyboardButton("🔄 تعویض کلید کلودفلر", callback_data="change_token")],
            [InlineKeyboardButton("❌ خروج", callback_data="cancel_action")]
        ]
        text = (
            f"👋 <b>منوی اصلی ربات:</b>\n\n"
            f"👤 اکانت متصل: <b>{account_name}</b>\n"
            "یکی از بخش‌های زیر را انتخاب کنید:"
        )
        await send_or_edit(update, text, InlineKeyboardMarkup(keyboard))
        return SELECT_WORKER
    else:
        keyboard = [
            [InlineKeyboardButton("🔗 باز کردن صفحه API Tokens", url=CLOUDFLARE_URL)],
            [InlineKeyboardButton("📊 آمار کاربران ربات", callback_data="bot_stats")],
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_action")]
        ]
        text = (
            "🔑 <b>ورود به ربات آپلود خودکار ورکر:</b>\n\n"
            "۱️⃣ روی دکمه زیر بزنید و قالب <b>Edit Cloudflare Workers</b> را بسازید.\n"
            "۲️⃣ بخش‌های <b>Account</b> و <b>Zone</b> را روی <b>All</b> بگذارید تا ارور ندهد.\n"
            "۳️⃣ کلید ساخته‌شده را کپی کنید و همین‌جا بفرستید:\n\n"
            "👇 <i>لطفاً کلید (API Token) کلودفلرتان را بفرستید:</i>"
        )
        await send_or_edit(update, text, InlineKeyboardMarkup(keyboard))
        return GET_TOKEN


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر شروع ربات"""
    user_id = update.effective_user.id
    await track_activity(user_id)

    user_data_raw = await db_command(["GET", f"user:{user_id}"])
    if user_data_raw:
        try:
            user_data = json.loads(user_data_raw)
            context.user_data["cf_token"] = user_data["cf_token"]
            context.user_data["account_id"] = user_data["account_id"]
            context.user_data["account_name"] = user_data.get("account_name", "اکانت شما")
        except Exception:
            pass

    return await show_main_menu(update, context)


async def get_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    user = update.effective_user
    await track_activity(user.id)

    status_msg = await update.message.reply_text("⏳ <i>در حال بررسی کلید و اتصال به کلودفلر...</i>", parse_mode="HTML")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            acc_res = await client.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
            acc_data = acc_res.json()

            if not acc_data.get("success") or not acc_data.get("result"):
                err = acc_data.get("errors", [{}])[0].get("message", "کلید نامعتبر است.")
                keyboard = [
                    [InlineKeyboardButton("🔗 صفحه ساخت کلید", url=CLOUDFLARE_URL)],
                    [InlineKeyboardButton("❌ لغو", callback_data="cancel_action")]
                ]
                await status_msg.edit_text(
                    f"❌ <b>خطا:</b> <code>{err}</code>\nلطفاً کلید صحیح را ارسال کنید:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                return GET_TOKEN

            account = acc_data["result"][0]
            context.user_data["cf_token"] = token
            context.user_data["account_id"] = account["id"]
            context.user_data["account_name"] = account["name"]

            # ذخیره در Upstash
            await db_command(["SET", f"user:{user.id}", json.dumps({
                "cf_token": token,
                "account_id": account["id"],
                "account_name": account["name"]
            })])

            await status_msg.delete()
            return await show_workers_menu(update, context)

        except Exception as e:
            logger.error(f"Auth error: {e}")
            await status_msg.edit_text("❌ خطا در اتصال به سرورهای کلودفلر!")
            return ConversationHandler.END


async def show_workers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.user_data.get("cf_token")
    account_id = context.user_data.get("account_id")
    account_name = context.user_data.get("account_name", "اکانت شما")

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            workers_res = await client.get(
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts",
                headers=headers
            )
            worker_list = [w["id"] for w in workers_res.json().get("result", [])]
            context.user_data["workers"] = worker_list

            keyboard = []
            for idx, name in enumerate(worker_list):
                keyboard.append([InlineKeyboardButton(f"📁 {name}", callback_data=f"w:{idx}")])

            keyboard.append([InlineKeyboardButton("➕ ساخت ورکر جدید", callback_data="new_worker")])
            keyboard.append([
                InlineKeyboardButton("📊 آمار ربات", callback_data="bot_stats"),
                InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")
            ])

            text = f"✅ اکانت: <b>{account_name}</b>\n\n👇 <b>ورکر مورد نظر را انتخاب کنید:</b>"
            await send_or_edit(update, text, InlineKeyboardMarkup(keyboard))
            return SELECT_WORKER
        except Exception as e:
            logger.error(f"Workers load error: {e}")
            await send_or_edit(update, "❌ خطا در دریافت لیست ورکرها!")
            return SELECT_WORKER


async def select_worker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    await track_activity(user_id)

    if data == "back_to_main":
        return await show_main_menu(update, context)

    elif data == "bot_stats":
        now = time.time()
        fifteen_mins_ago = now - 900
        total_users = await db_command(["SCARD", "bot_all_users"]) or 0
        active_users = await db_command(["ZCOUNT", "bot_active_users", fifteen_mins_ago, "+inf"]) or 0

        stats_text = (
            "📊 <b>آمار همگانی کاربران ربات:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>تعداد کل کاربران:</b> <code>{total_users}</code> نفر\n"
            f"🟢 <b>کاربران آنلاین و فعال:</b> <code>{active_users}</code> نفر (۱۵ دقیقه اخیر)\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]
        await send_or_edit(update, stats_text, InlineKeyboardMarkup(keyboard))
        return SELECT_WORKER

    elif data == "load_workers":
        return await show_workers_menu(update, context)

    elif data == "change_token":
        keyboard = [
            [InlineKeyboardButton("🔗 باز کردن صفحه API Tokens", url=CLOUDFLARE_URL)],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
        ]
        text = "🔑 لطفاً کلید (API Token) جدید کلودفلر خود را ارسال کنید:"
        await send_or_edit(update, text, InlineKeyboardMarkup(keyboard))
        return GET_TOKEN

    elif data == "cancel_action":
        await send_or_edit(update, "🚫 عملیات لغو شد. برای شروع مجدد /start را بزنید.")
        return ConversationHandler.END

    elif data == "new_worker":
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به لیست ورکرها", callback_data="load_workers")]]
        await send_or_edit(
            update,
            "📝 نام انگلیسی ورکر جدید را بفرستید (یا /random بزنید):",
            InlineKeyboardMarkup(keyboard)
        )
        return NEW_WORKER_NAME

    elif data.startswith("w:"):
        idx = int(data.split(":")[1])
        worker_name = context.user_data["workers"][idx]
        context.user_data["worker_name"] = worker_name
        return await show_worker_panel(update, context)


async def show_worker_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    worker_name = context.user_data["worker_name"]
    keyboard = [
        [InlineKeyboardButton("🚀 آپلود / تعویض کد worker.js", callback_data="w_upload")],
        [InlineKeyboardButton("🔐 مدیریت Secret ها (متغیرهای رمزشده)", callback_data="w_secrets")],
        [InlineKeyboardButton("🗄 ساخت و اتصال دیتابیس KV", callback_data="w_kv")],
        [InlineKeyboardButton("💾 ساخت و اتصال دیتابیس D1 (SQL)", callback_data="w_d1")],
        [InlineKeyboardButton("🔙 بازگشت به لیست ورکرها", callback_data="load_workers")]
    ]
    text = f"🎯 <b>مدیریت ورکر:</b> <code>{worker_name}</code>\n\nیک گزینه را انتخاب کنید:"
    await send_or_edit(update, text, InlineKeyboardMarkup(keyboard))
    return WORKER_PANEL


async def handle_worker_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    worker_name = context.user_data.get("worker_name", "worker")

    if data == "load_workers":
        return await show_workers_menu(update, context)

    elif data == "back_panel":
        return await show_worker_panel(update, context)

    elif data == "w_upload":
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]]
        await send_or_edit(
            update,
            f"📄 فایل <code>worker.js</code> یا متن کد را برای ورکر <b>{worker_name}</b> بفرستید:",
            InlineKeyboardMarkup(keyboard)
        )
        return GET_FILE

    elif data == "w_secrets":
        token = context.user_data["cf_token"]
        account_id = context.user_data["account_id"]
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            sec_res = await client.get(
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/secrets",
                headers=headers
            )
            secrets_list = [s["name"] for s in sec_res.json().get("result", [])]

        sec_text = "<b>لیست Secret های فعال:</b>\n"
        if secrets_list:
            for s in secrets_list:
                sec_text += f"• <code>{s}</code>\n"
        else:
            sec_text += "<i>هیچ Secretی ثبت نشده است.</i>\n"

        keyboard = [
            [InlineKeyboardButton("➕ افزودن Secret جدید", callback_data="add_secret")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]
        ]
        await send_or_edit(update, sec_text, InlineKeyboardMarkup(keyboard))
        return WORKER_PANEL

    elif data == "add_secret":
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="w_secrets")]]
        await send_or_edit(
            update,
            "📝 لطفاً <b>نام Secret</b> را بفرستید (مثلاً: <code>UUID</code>):",
            InlineKeyboardMarkup(keyboard)
        )
        return GET_SEC_NAME

    elif data == "w_kv":
        keyboard = [
            [InlineKeyboardButton("➕ ساخت KV و اتصال به ورکر", callback_data="create_kv")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]
        ]
        await send_or_edit(update, "🗄 <b>پایگاه داده Workers KV:</b>\nبرای ساخت و بایند کلیک کنید:", InlineKeyboardMarkup(keyboard))
        return WORKER_PANEL

    elif data == "create_kv":
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_panel")]]
        await send_or_edit(update, "📝 نام متغیر KV را بفرستید (پیش‌فرض: <code>MY_KV</code>):", InlineKeyboardMarkup(keyboard))
        return GET_KV_NAME

    elif data == "w_d1":
        keyboard = [
            [InlineKeyboardButton("➕ ساخت دیتابیس D1 و اتصال", callback_data="create_d1")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]
        ]
        await send_or_edit(update, "💾 <b>دیتابیس Cloudflare D1 SQL:</b>\nبرای ساخت و بایند کلیک کنید:", InlineKeyboardMarkup(keyboard))
        return WORKER_PANEL

    elif data == "create_d1":
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_panel")]]
        await send_or_edit(update, "📝 نام متغیر دیتابیس D1 را بفرستید (پیش‌فرض: <code>DB</code>):", InlineKeyboardMarkup(keyboard))
        return GET_D1_NAME


async def get_secret_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sec_name"] = update.message.text.strip().upper()
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="w_secrets")]]
    await update.message.reply_text(
        f"🔐 نام سکرت: <code>{context.user_data['sec_name']}</code>\n\nمقدار آن را ارسال کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return GET_SEC_VAL


async def get_secret_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec_val = update.message.text.strip()
    sec_name = context.user_data["sec_name"]
    worker_name = context.user_data["worker_name"]
    token = context.user_data["cf_token"]
    account_id = context.user_data["account_id"]

    status_msg = await update.message.reply_text("⏳ <i>در حال ثبت Secret در کلودفلر...</i>", parse_mode="HTML")

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/secrets"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"name": sec_name, "text": sec_val, "type": "secret_text"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.put(url, headers=headers, json=body)
        if res.json().get("success"):
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]]
            await status_msg.edit_text(
                f"✅ سکرت <code>{sec_name}</code> متصل شد!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            err = res.json().get("errors", [{}])[0].get("message", "خطا")
            await status_msg.edit_text(f"❌ خطا: <code>{err}</code>")
    return WORKER_PANEL


async def get_kv_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kv_var = update.message.text.strip().upper().replace(" ", "_")
    worker_name = context.user_data["worker_name"]
    token = context.user_data["cf_token"]
    account_id = context.user_data["account_id"]

    status_msg = await update.message.reply_text("⚙️ <i>در حال ساخت و بایند KV...</i>", parse_mode="HTML")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=25.0) as client:
        kv_res = await client.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces",
            headers=headers,
            json={"title": f"{worker_name}-{kv_var}".lower()}
        )
        kv_data = kv_res.json()
        if not kv_data.get("success"):
            err = kv_data.get("errors", [{}])[0].get("message", "خطا")
            await status_msg.edit_text(f"❌ خطا: <code>{err}</code>")
            return WORKER_PANEL

        ns_id = kv_data["result"]["id"]
        await client.patch(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/settings",
            headers=headers,
            json={"bindings": [{"type": "kv_namespace", "name": kv_var, "namespace_id": ns_id}]}
        )

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]]
        await status_msg.edit_text(
            f"🎉 <b>دیتابیس KV متصل شد!</b>\nمتغیر: <code>env.{kv_var}</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    return WORKER_PANEL


async def get_d1_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d1_var = update.message.text.strip().upper().replace(" ", "_")
    worker_name = context.user_data["worker_name"]
    token = context.user_data["cf_token"]
    account_id = context.user_data["account_id"]

    status_msg = await update.message.reply_text("⚙️ <i>در حال ساخت و بایند دیتابیس D1 SQL...</i>", parse_mode="HTML")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=25.0) as client:
        d1_res = await client.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database",
            headers=headers,
            json={"name": f"{worker_name}-{d1_var}".lower()}
        )
        d1_data = d1_res.json()
        if not d1_data.get("success"):
            err = d1_data.get("errors", [{}])[0].get("message", "خطا")
            await status_msg.edit_text(f"❌ خطا: <code>{err}</code>")
            return WORKER_PANEL

        d1_id = d1_data["result"]["uuid"]
        await client.patch(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/settings",
            headers=headers,
            json={"bindings": [{"type": "d1", "name": d1_var, "id": d1_id}]}
        )

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]]
        await status_msg.edit_text(
            f"🎉 <b>دیتابیس D1 SQL متصل شد!</b>\nمتغیر: <code>env.{d1_var}</code>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    return WORKER_PANEL


async def new_worker_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    worker_name = f"worker-{secrets.token_hex(4)}" if text.lower() == "/random" else text.lower().replace(" ", "-")
    context.user_data["worker_name"] = worker_name
    return await show_worker_panel(update, context)


async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    js_code = ""
    if update.message.document:
        doc = update.message.document
        file = await context.bot.get_file(doc.file_id)
        js_code = (await file.download_as_bytearray()).decode("utf-8")
    elif update.message.text:
        js_code = update.message.text

    if not js_code or len(js_code.strip()) < 10:
        await update.message.reply_text("❌ کدی یافت نشد! لطفاً فایل یا متن کد را بفرستید:")
        return GET_FILE

    token = context.user_data["cf_token"]
    account_id = context.user_data["account_id"]
    worker_name = context.user_data["worker_name"]

    status_msg = await update.message.reply_text(f"🚀 <i>در حال آپلود کد روی {worker_name}...</i>", parse_mode="HTML")

    headers = {"Authorization": f"Bearer {token}"}
    files = {
        "metadata": (None, json.dumps({"main_module": "worker.js"}), "application/json"),
        "worker.js": ("worker.js", js_code.encode("utf-8"), "application/javascript+module")
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}"
            res = await client.put(upload_url, headers=headers, files=files)
            if not res.json().get("success"):
                err = res.json().get("errors", [{}])[0].get("message", "خطا")
                await status_msg.edit_text(f"❌ خطا: <code>{err}</code>")
                return WORKER_PANEL

            await client.post(
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{worker_name}/subdomain",
                headers=headers,
                json={"enabled": True}
            )

            sub_res = await client.get(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/subdomain", headers=headers)
            sub_name = sub_res.json().get("result", {}).get("subdomain", "")
            worker_url = f"https://{worker_name}.{sub_name}.workers.dev" if sub_name else "در کلودفلر فعال شد"

            keyboard = [
                [InlineKeyboardButton("🌐 باز کردن ورکر", url=worker_url)],
                [InlineKeyboardButton("🔙 بازگشت به پنل ورکر", callback_data="back_panel")]
            ]
            await status_msg.edit_text(
                f"🎉 <b>کد با موفقیت منتشر شد!</b>\n\n🔗 <code>{worker_url}</code>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return WORKER_PANEL

        except Exception as e:
            logger.error(f"Deploy error: {e}")
            await status_msg.edit_text("❌ خطا در آپلود ورکر!")
            return WORKER_PANEL


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_or_edit(update, "🚫 عملیات لغو شد. برای شروع مجدد /start را بزنید.")
    return ConversationHandler.END


def main():
    if not BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN_HERE" in BOT_TOKEN:
        print("❌ خطا: لطفاً توکن ربات تلگرام را در متغیر TELEGRAM_BOT_TOKEN یا خط ۲۸ وارد کنید!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_token),
                CallbackQueryHandler(select_worker)
            ],
            SELECT_WORKER: [CallbackQueryHandler(select_worker)],
            WORKER_PANEL: [CallbackQueryHandler(handle_worker_panel)],
            NEW_WORKER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, new_worker_name),
                CallbackQueryHandler(select_worker)
            ],
            GET_FILE: [
                MessageHandler(filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), get_file),
                CallbackQueryHandler(handle_worker_panel)
            ],
            GET_SEC_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_secret_name),
                CallbackQueryHandler(handle_worker_panel)
            ],
            GET_SEC_VAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_secret_val),
                CallbackQueryHandler(handle_worker_panel)
            ],
            GET_KV_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_kv_name),
                CallbackQueryHandler(handle_worker_panel)
            ],
            GET_D1_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_d1_name),
                CallbackQueryHandler(handle_worker_panel)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel)
        ],
        allow_reentry=True,  # این گزینه تضمین می‌کند دستور /start همیشه و در هر مرحله‌ای کار کند
    )

    app.add_handler(conv_handler)
    print("🤖 Bot is running smoothly...")
    app.run_polling()


if __name__ == "__main__":
    main()