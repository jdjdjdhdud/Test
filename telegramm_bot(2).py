import logging
import os
import re
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# تنظیمات
TOKEN = "8452409930:AAH0gIK6bdvPnehTmKOJbYKLR2VEPY6k4PE"  # توکن ربات خود را اینجا قرار دهید
if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("لطفاً توکن ربات خود را در متغیر TOKEN قرار دهید")

ADMIN_IDS = [7770582235,8263205787 ]  # آیدی مدیران
CHANNEL_USERNAME = "@KIA_YT0610"  # چنل اجباری اصلی
ADDITIONAL_CHANNELS = []  # چنل‌های اضافی اجباری

# Dictionary to track user states
user_states = {}
user_blocked = set()

# سیستم کد تخفیف - ذخیره کدها، درصد تخفیف و محصولات قابل اعمال
discount_codes = {}  
# فرمت: {"Kiyayt50": {"discount": 10, "product": "config_basic"}}

# سیستم کدهای تمدید
extension_codes = {}
# فرمت: {"EXT001": {"user_id": 123456, "product": "config_basic", "price": 77000, "valid": True}}

# متن‌های قابل ویرایش توسط مدیر
editable_texts = {
    'tutorial_android': 'درحال اپدیت',
    'tutorial_ios': 'درحال اپدیت', 
    'tutorial_pc': 'درحال اپدیت',
    'rules_text': 'درحال اپدیت',
    'android_cheat': 'درحال اپدیت',
    'ios_cheat': 'درحال اپدیت',
    'mandatory_membership': True,
    'anti_spam_enabled': False,
    'anti_spam_limit': 5,  # حداکثر تعداد پیام در دقیقه
}

# تنظیمات پرداخت
payment_settings = {
    'card_number': '5859831176852845',
    'card_holder': 'کیارش ارامیده'
}

# اطلاعات محصولات و قیمت‌ها
PRODUCTS = {
    # Android/iOS محصولات
    "config_basic": {"name": "کانفیگ بیسیک", "price": 154000, "code": "CB001"},
    "config_custom": {"name": "کانفیگ کاستوم", "price": 321000, "code": "CC002"},
    "config_private": {"name": "کانفیگ خصوصی", "price": 525000, "code": "CP003"},
    
    # Android چیت
    "android_cheat": {"name": "چیت اندروید", "price": 200000, "code": "AC001"},
    
    # iOS چیت
    "ios_cheat": {"name": "چیت آیفون", "price": 200000, "code": "IC001"},
    
    # PC محصولات جدید
    "pc_config_basic": {"name": "کانفیگ BASIC بیسیک", "price": 350000, "code": "PC001"},
    "pc_config_vvip": {"name": "کانفیگ VVIP وی وی آی پی", "price": 450000, "code": "PC002"},
    "pc_config_custom": {"name": "کانفیگ custom کاستوم", "price": 550000, "code": "PC003"},
    "pc_config_private": {"name": "کانفیگ private خصوصی", "price": 700000, "code": "PC004"},
    
    # محصولات هاست
    "host_basic": {"name": "هاست اختصاصی بیسیک", "price": 231000, "code": "HOST001"},
    "host_vip": {"name": "هاست اختصاصی VIP", "price": 321000, "code": "HOST002"},
    "host_custom": {"name": "هاست اختصاصی کاستوم", "price": 432000, "code": "HOST003"},
    
    # DNS محصولات
    "dns_bronze": {"name": "DNS برنز", "price": 80000, "code": "DNS001"},
    "dns_platinum": {"name": "DNS پلاتینیوم", "price": 130000, "code": "DNS002"},
    "dns_elite": {"name": "DNS آلیت", "price": 230000, "code": "DNS003"},
    "dns_exclusive": {"name": "DNS اکسکلوسیو", "price": 330000, "code": "DNS004"},
    "dns_legendary": {"name": "DNS لجندری", "price": 435000, "code": "DNS005"},
    
    # WireGuard محصولات
    "wireguard_single": {"name": "وایرگاد تک لوکیشن", "price": 123000, "code": "WG001"},
    "wireguard_dual": {"name": "وایرگاد دو لوکیشن", "price": 231000, "code": "WG002"},
    "wireguard_triple": {"name": "وایرگاد سه لوکیشن", "price": 321000, "code": "WG003"},
    
    # سایت محصولات
    "site_premium": {"name": "سایت ویژه", "price": 800000, "code": "SP001"},
    "site_normal": {"name": "سایت عادی", "price": 400000, "code": "SN001"},
    
    # فیکس لگ محصولات
    "fixlag_basic": {"name": "فیکس لگ", "price": 80000, "code": "FL001", "duration": "40 روز"},
    "fixlag_fps": {"name": "کانفیگ افزایش FPS", "price": 145000, "code": "FL002", "duration": "40 روز"},
    "fixlag_fps_plus": {"name": "کانفیگ FPS + کاهش لگ", "price": 235000, "code": "FL003", "duration": "40 روز"},
}

# آمار و گزارشات
user_stats = {
    'total_users': set(),  # مجموع کاربران
    'active_users_today': set(),  # کاربران فعال امروز
    'receipts_submitted': 0,  # رسیدهای ارسالی
    'successful_purchases': 0,  # خریدهای موفق
    'total_revenue': 0,  # درآمد کل
    'discount_codes_used': 0,  # کدهای تخفیف استفاده شده
}

# آمار محصولات
product_stats = {}
for product_key in PRODUCTS.keys():
    product_stats[product_key] = {
        'purchases': 0,
        'revenue': 0,
        'discount_usage': 0
    }

# سیستم آنتی اسپم
user_message_count = {}  # برای شمارش پیام‌ها

# اطلاعات کاربران (موجودی، تعداد سفارشات، نام)
user_data = {}

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# کاهش سطح لاگ httpx برای جلوگیری از نمایش توکن
logging.getLogger("httpx").setLevel(logging.WARNING)

# ذخیره file_id ویدیوها برای محصولات مختلف (باید توسط مدیر آپلود شوند)
SITE_VIDEO_FILE_ID = None
PRODUCT_VIDEOS = {}  # دیکشنری برای نگهداری file_id ویدیو هر محصول

# سیستم ذخیره‌سازی داده‌ها
def save_user_data():
    """ذخیره کردن اطلاعات کاربران در فایل JSON"""
    try:
        # تبدیل setها به لیست برای ذخیره در JSON
        data_to_save = {
            'user_data': user_data,
            'user_stats': {
                'total_users': list(user_stats['total_users']),
                'active_users_today': list(user_stats['active_users_today']),
                'receipts_submitted': user_stats['receipts_submitted'],
                'successful_purchases': user_stats['successful_purchases'],
                'total_revenue': user_stats['total_revenue'],
                'discount_codes_used': user_stats['discount_codes_used'],
            },
            'user_blocked': list(user_blocked),
            'discount_codes': discount_codes,
            'extension_codes': extension_codes,
            'product_stats': product_stats,
            'editable_texts': editable_texts,
            'payment_settings': payment_settings,
            'additional_channels': ADDITIONAL_CHANNELS
        }
        
        with open('user_data.json', 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در ذخیره داده‌ها: {e}")

def load_user_data():
    """بارگذاری اطلاعات کاربران از فایل JSON"""
    global user_data, user_stats, user_blocked, discount_codes, extension_codes, product_stats, editable_texts, payment_settings, ADDITIONAL_CHANNELS
    
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        user_data = data.get('user_data', {})
        
        # تبدیل لیست‌ها به set
        loaded_stats = data.get('user_stats', {})
        user_stats['total_users'] = set(loaded_stats.get('total_users', []))
        user_stats['active_users_today'] = set(loaded_stats.get('active_users_today', []))
        user_stats['receipts_submitted'] = loaded_stats.get('receipts_submitted', 0)
        user_stats['successful_purchases'] = loaded_stats.get('successful_purchases', 0)
        user_stats['total_revenue'] = loaded_stats.get('total_revenue', 0)
        user_stats['discount_codes_used'] = loaded_stats.get('discount_codes_used', 0)
        
        user_blocked = set(data.get('user_blocked', []))
        discount_codes = data.get('discount_codes', {})
        extension_codes = data.get('extension_codes', {})
        product_stats = data.get('product_stats', product_stats)
        editable_texts.update(data.get('editable_texts', {}))
        payment_settings.update(data.get('payment_settings', {}))
        ADDITIONAL_CHANNELS[:] = data.get('additional_channels', [])
        
        logger.info("داده‌ها با موفقیت بارگذاری شدند")
        
    except FileNotFoundError:
        logger.info("فایل داده یافت نشد، از داده‌های پیش‌فرض استفاده می‌شود")
        save_user_data()  # ایجاد فایل اولیه
    except Exception as e:
        logger.error(f"خطا در بارگذاری داده‌ها: {e}")

# بررسی آنتی اسپم
def check_anti_spam(user_id):
    """بررسی آنتی اسپم کاربر"""
    if not editable_texts.get('anti_spam_enabled', False):
        return True
        
    current_time = datetime.now()
    if user_id not in user_message_count:
        user_message_count[user_id] = []
    
    # حذف پیام‌های قدیمی (بیشتر از 1 دقیقه)
    user_message_count[user_id] = [
        msg_time for msg_time in user_message_count[user_id] 
        if (current_time - msg_time).seconds < 60
    ]
    
    # بررسی حد مجاز
    if len(user_message_count[user_id]) >= editable_texts.get('anti_spam_limit', 5):
        return False
    
    # اضافه کردن زمان پیام فعلی
    user_message_count[user_id].append(current_time)
    return True

def get_user_info(user_id):
    """دریافت اطلاعات کاربر"""
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'balance': 0,
            'orders': 0,
            'orders_count': 0,
            'first_name': '',
            'username': '',
            'join_date': datetime.now().isoformat(),
            'referrals': 0,
            'used_referral': False,
            'referred_by': None
        }
        save_user_data()
    return user_data[str(user_id)]

def update_user_balance(user_id, amount):
    """به‌روزرسانی موجودی کاربر"""
    user_info = get_user_info(user_id)
    user_info['balance'] += amount
    save_user_data()

def increase_user_orders(user_id):
    """افزایش تعداد سفارشات کاربر"""
    user_info = get_user_info(user_id)
    user_info['orders_count'] += 1
    save_user_data()

# بررسی عضویت چنل
async def check_channel_membership(bot, user_id):
    """بررسی عضویت کاربر در چنل"""
    if not editable_texts.get('mandatory_membership', True):
        return True
    
    # بررسی چنل اصلی
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت چنل اصلی: {e}")
        return False
    
    # بررسی چنل‌های اضافی
    for channel in ADDITIONAL_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت چنل {channel}: {e}")
            return False
    
    return True

# ارسال پیام همگانی
async def broadcast_message(bot, message_text, admin_id):
    """ارسال پیام همگانی به همه کاربران"""
    import asyncio
    success_count = 0
    failed_count = 0
    
    for user_id in user_stats['total_users']:
        if user_id == admin_id:  # خود مدیر رو رد کن
            continue
            
        try:
            await bot.send_message(user_id, message_text)
            success_count += 1
            await asyncio.sleep(0.1)  # تاخیر کوتاه برای جلوگیری از spam
        except Exception as e:
            failed_count += 1
            logger.error(f"خطا در ارسال پیام به {user_id}: {e}")
    
    return success_count, failed_count

# منوی اصلی
def main_menu(user_id=None):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید", callback_data="buy")],
        [InlineKeyboardButton("🔄 تمدید", callback_data="extension_request")],
        [InlineKeyboardButton("📚 آموزش", callback_data="tutorial")],
        [InlineKeyboardButton("🌐 سایت", callback_data="site")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="user_account")],
        [InlineKeyboardButton("📞 ارتباط با پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("📱 آپدیت محصولات", callback_data="updates")]
    ]
    
    # اضافه کردن پنل مدیریت کامل فقط برای مالکین
    if user_id and user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("👨‍💼 پنل مدیریت", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# پنل مدیریت اصلاح شده
def admin_panel_menu():
    keyboard = [
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("💰 گزارش فروش", callback_data="admin_sales")],
        [InlineKeyboardButton("📋 رسیدهای ارسالی", callback_data="admin_receipts")],
        [InlineKeyboardButton("📈 آمار محصولات", callback_data="admin_products")],
        [InlineKeyboardButton("🎫 پنل کد تخفیف", callback_data="discount_codes_panel")],
        [InlineKeyboardButton("🔄 تمدید", callback_data="admin_extension")],
        [InlineKeyboardButton("🔗 عضویت اجباری", callback_data="admin_membership")],
        [InlineKeyboardButton("📜 قوانین", callback_data="admin_rules")],
        [InlineKeyboardButton("🛡️ آنتی اسپم", callback_data="admin_antispam")],
        [InlineKeyboardButton("📝 متن ربات", callback_data="admin_texts")],
        [InlineKeyboardButton("💳 تنظیمات پرداخت", callback_data="admin_payment")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎥 مدیریت ویدیو سایت", callback_data="admin_site_video")],
        [InlineKeyboardButton("📹 مدیریت ویدیو محصولات", callback_data="admin_product_videos")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ایجاد دکمه‌های خرید برای محصولات
def create_purchase_buttons(product_key, back_callback, user_id=None):
    # اگر کاربر از یکی از پلتفرم‌ها اومده، از context پلتفرم استفاده کن
    if user_id and user_id in user_states and 'platform_context' in user_states[user_id]:
        platform = user_states[user_id]['platform_context']
        if 'config' in back_callback:
            back_callback = f"{platform}_config"
        elif 'dns' in back_callback:
            back_callback = f"{platform}_dns" 
        elif 'wireguard' in back_callback:
            back_callback = f"{platform}_wireguard"
        elif 'host' in back_callback:
            back_callback = f"{platform}_host"
    
    keyboard = [
        [InlineKeyboardButton("💳 کارت به کارت", callback_data=f"payment_{product_key}")],
        [InlineKeyboardButton("💰 کسر از موجودی", callback_data=f"balance_{product_key}")],
        [InlineKeyboardButton("🎫 کد تخفیف", callback_data=f"discount_{product_key}")],
        [InlineKeyboardButton("📜 قوانین", callback_data="show_rules")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)]
    ]
    return InlineKeyboardMarkup(keyboard)

# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
        
    user = update.effective_user
    user_id = user.id
    
    # بررسی آنتی اسپم
    if not check_anti_spam(user_id):
        await update.message.reply_text("⚠️ شما خیلی سریع پیام می‌فرستید. لطفاً کمی صبر کنید.")
        return
    
    # بررسی رفرال از لینک start
    referrer_id = None
    if context.args and context.args[0].startswith('ref_'):
        try:
            referrer_id = int(context.args[0].replace('ref_', ''))
            # مطمئن شویم که کاربر قبلاً از رفرال استفاده نکرده
            user_info = get_user_info(user_id)
            if not user_info.get('used_referral', False) and referrer_id != user_id:
                # اضافه کردن 2000 تومان به حساب معرف
                referrer_info = get_user_info(referrer_id)
                referrer_info['balance'] += 2000
                referrer_info['referrals'] = referrer_info.get('referrals', 0) + 1
                
                # علامت‌گذاری که این کاربر از رفرال استفاده کرده
                user_info['used_referral'] = True
                user_info['referred_by'] = referrer_id
                
                save_user_data()
                
                # اطلاع به معرف
                try:
                    await context.bot.send_message(
                        referrer_id,
                        f"🎉 کاربر جدید از لینک رفرال شما وارد شد!\n\n👤 {user.first_name or 'کاربر جدید'}\n💰 مبلغ 2000 تومان اضافه شد"
                    )
                except Exception:
                    pass  # اگر نتونست پیام بفرسته مشکلی نیست
                    
        except (ValueError, IndexError):
            pass  # اگر فرمت رفرال اشتباه بود نادیده بگیر
    
    # ذخیره اطلاعات کاربر
    user_info = get_user_info(user_id)
    user_info['first_name'] = user.first_name or ''
    user_info['username'] = user.username or ''
    save_user_data()
    
    # بررسی عضویت چنل (مگر برای ادمین‌ها)
    if user_id not in ADMIN_IDS:
        is_member = await check_channel_membership(context.bot, user_id)
        if not is_member:
            # ساخت لیست چنل‌ها برای نمایش
            channels_text = f"{CHANNEL_USERNAME}"
            keyboard = [[InlineKeyboardButton("🔗 عضویت در چنل اصلی", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
            
            # اضافه کردن چنل‌های اضافی
            if ADDITIONAL_CHANNELS:
                channels_text += "\n\n📋 چنل‌های اضافی اجباری:"
                for i, channel in enumerate(ADDITIONAL_CHANNELS, 1):
                    channels_text += f"\n{i}. {channel}"
                    keyboard.append([InlineKeyboardButton(f"🔗 چنل {i}", url=f"https://t.me/{channel[1:] if channel.startswith('@') else channel}")])
            
            keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")])
            
            await update.message.reply_text(
                f"🔐 برای استفاده از ربات، ابتدا باید در چنل‌های زیر عضو شوید:\n\n{channels_text}\n\nپس از عضویت در همه چنل‌ها، دکمه '✅ عضو شدم' را بزنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # اضافه کردن کاربر به آمار
    user_stats['total_users'].add(user_id)
    user_stats['active_users_today'].add(user_id)
    save_user_data()
    
    # بررسی مسدود بودن کاربر
    if user_id in user_blocked:
        await update.message.reply_text("🚫 شما از استفاده از این ربات محروم شده‌اید.")
        return
    
    welcome_text = f"""
🌟 سلام {user.first_name} عزیز!

به ربات خدمات ما خوش اومدی 🎉

از منوی زیر می‌تونی استفاده کنی:
"""
    await update.message.reply_text(welcome_text, reply_markup=main_menu(user_id))

# پردازش پرداخت ریالی
async def process_payment(query, product_key):
    if product_key not in PRODUCTS:
        try:
            await query.edit_message_text("❌ محصول مورد نظر یافت نشد!")
        except Exception:
            await query.message.reply_text("❌ محصول مورد نظر یافت نشد!")
        return
    
    product = PRODUCTS[product_key]
    
    # ذخیره اطلاعات خرید کاربر
    user_states[query.from_user.id] = {
        'waiting_for_receipt': True,
        'product_key': product_key,
        'product_name': product['name'],
        'product_code': product['code'],
        'amount': product['price'],
        'discount_applied': False,
        'discount_code': None,
        'discount_amount': 0
    }
    
    card_number = payment_settings.get('card_number', '5859831176852845')
    card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
    
    payment_text = f"""
☑️ ممنون از انتخاب و اعتماد شما
لطفا مبلغ {product['price']:,} تومان به کارت زیر واریز کنید

💳 شماره کارت:
{card_number}
بنام {card_holder}

لطفاً رسید و عکس کسر موجودی با کد محصول رو بفرستید ✅
📱 کد محصول: {product['code']}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    
    try:
        await query.edit_message_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        # اگه نتونست پیام رو ویرایش کنه (مثلاً چون ویدیو ارسال شده)، پیام جدید می‌فرسته
        await query.message.reply_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))

# فانکشن جدید برای استخراج درصد تخفیف از کد
def extract_discount_percentage(code):
    """استخراج درصد تخفیف از اعداد آخر کد"""
    import re
    # پیدا کردن اعداد در آخر کد
    numbers = re.findall(r'\d+', code)
    if numbers:
        # آخرین عدد پیدا شده را به عنوان درصد تخفیف برگردان
        percentage = int(numbers[-1])
        return min(percentage, 100)  # حداکثر 100%
    return 0

# فانکشن جدید برای بررسی کاربرد کد برای محصول
def can_apply_discount_to_product(discount_category, product_key):
    """بررسی اینکه کد تخفیف برای محصول قابل اعمال است یا نه"""
    if discount_category == "همه محصولات":
        return True
    
    # بررسی دقیق برای محصولات خاص
    specific_products = {
        "کانفیگ بیسیک": ["config_basic"],
        "کانفیگ کاستوم": ["config_custom"], 
        "کانفیگ خصوصی": ["config_private"],
        "چیت اندروید": ["android_cheat"],
        "چیت آیفون": ["ios_cheat"],
        "کانفیگ PC بیسیک": ["pc_config_basic"],
        "کانفیگ PC VVIP": ["pc_config_vvip"],
        "کانفیگ PC کاستوم": ["pc_config_custom"],
        "کانفیگ PC خصوصی": ["pc_config_private"],
        "هاست بیسیک": ["host_basic"],
        "هاست VIP": ["host_vip"],
        "هاست کاستوم": ["host_custom"],
        "DNS برنز": ["dns_bronze"],
        "DNS پلاتینیوم": ["dns_platinum"],
        "DNS آلیت": ["dns_elite"],
        "DNS اکسکلوسیو": ["dns_exclusive"],
        "DNS لجندری": ["dns_legendary"],
        "وایرگاد تک لوکیشن": ["wireguard_single"],
        "وایرگاد دو لوکیشن": ["wireguard_dual"],
        "وایرگاد سه لوکیشن": ["wireguard_triple"],
        "سایت نسخه ویژه": ["site_premium"],
        "سایت نسخه عادی": ["site_normal"],
        "فیکس لگ": ["fixlag_basic"],
        "کانفیگ افزایش FPS": ["fixlag_fps"],
        "کانفیگ FPS + کاهش لگ": ["fixlag_fps_plus"],
    }
    
    # بررسی محصول خاص
    if discount_category in specific_products:
        return product_key in specific_products[discount_category]
    
    # بررسی کلی دسته‌ها
    general_categories = {
        "کانفیگ": ["config_basic", "config_custom", "config_private"],
        "چیت": ["android_cheat", "ios_cheat"],
        "PC": ["pc_config_basic", "pc_config_vvip", "pc_config_custom", "pc_config_private"],
        "هاست": ["host_basic", "host_vip", "host_custom"],
        "DNS": ["dns_bronze", "dns_platinum", "dns_elite", "dns_exclusive", "dns_legendary"],
        "وایرگاد": ["wireguard_single", "wireguard_dual", "wireguard_triple"],
        "سایت": ["site_premium", "site_normal"],
        "فیکس لگ": ["fixlag_basic", "fixlag_fps", "fixlag_fps_plus"]
    }
    
    return product_key in general_categories.get(discount_category, [])

# فانکشن‌های جدید برای مدیریت تمدید محصولات
def get_products_by_category(category):
    """دریافت محصولات بر اساس دسته‌بندی"""
    product_categories = {
        "android_config": ["config_basic", "config_custom", "config_private"],
        "android_dns": ["dns_bronze", "dns_platinum", "dns_elite", "dns_exclusive", "dns_legendary"],
        "android_wireguard": ["wireguard_single", "wireguard_dual", "wireguard_triple"],
        "android_host": ["host_basic", "host_vip", "host_custom"],
        "android_fixlag": ["fixlag_basic", "fixlag_fps", "fixlag_fps_plus"],
        "ios_cheat": ["ios_cheat"],
        "ios_dns": ["dns_bronze", "dns_platinum", "dns_elite", "dns_exclusive", "dns_legendary"],
        "ios_wireguard": ["wireguard_single", "wireguard_dual", "wireguard_triple"],
        "pc_config": ["pc_config_basic", "pc_config_vvip", "pc_config_custom", "pc_config_private"],
        "pc_dns": ["dns_bronze", "dns_platinum", "dns_elite", "dns_exclusive", "dns_legendary"],
        "pc_wireguard": ["wireguard_single", "wireguard_dual", "wireguard_triple"],
        "pc_host": ["host_basic", "host_vip", "host_custom"],
        "pc_fixlag": ["fixlag_basic", "fixlag_fps", "fixlag_fps_plus"]
    }
    return product_categories.get(category, [])

def create_renewal_buttons(category, back_callback):
    """ایجاد دکمه‌های تمدید برای محصولات"""
    products = get_products_by_category(category)
    keyboard = []
    
    for product_key in products:
        if product_key in PRODUCTS:
            product = PRODUCTS[product_key]
            keyboard.append([InlineKeyboardButton(
                f"🔄 تمدید {product['name']}", 
                callback_data=f"renew_{product_key}"
            )])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(keyboard)

def create_products_text(category, title):
    """ایجاد متن نمایش محصولات"""
    products = get_products_by_category(category)
    text = f"{title}\n\n"
    
    for i, product_key in enumerate(products, 1):
        if product_key in PRODUCTS:
            product = PRODUCTS[product_key]
            duration = product.get('duration', '')
            duration_text = f" - {duration}" if duration else ""
            text += f"{i}. {product['name']}{duration_text}\n📱 کد: {product['code']}\n💰 قیمت: {product['price']:,} تومان\n\n"
    
    text += "لطفاً محصول مورد نظر برای تمدید را انتخاب کنید:"
    return text

# پردازش تمدید محصولات
async def process_product_renewal(query, product_key):
    """پردازش درخواست تمدید محصول"""
    user_id = query.from_user.id
    
    if product_key not in PRODUCTS:
        await query.answer("❌ محصول مورد نظر یافت نشد!", show_alert=True)
        return
    
    product = PRODUCTS[product_key]
    
    # تنظیم state برای تمدید
    user_states[user_id] = {
        'waiting_for_update_receipt': True,
        'product_key': product_key,
        'product_name': product['name'],
        'product_code': product['code'],
        'renewal_request': True  # علامت برای تشخیص تمدید از خرید عادی
    }
    
    card_number = payment_settings.get('card_number', '5859831176852845')
    card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
    
    renewal_text = f"""🔄 تمدید محصول

🛍️ محصول: {product['name']}
📱 کد محصول: {product['code']}
💰 قیمت: {product['price']:,} تومان

☑️ لطفا مبلغ {product['price']:,} تومان به کارت زیر واریز کنید

💳 شماره کارت:
{card_number}
بنام {card_holder}

لطفاً رسید و عکس کسر موجودی با اطلاعات زیر ارسال کنید:
📱 کد محصول: {product['code']}
🔄 نوع درخواست: تمدید

⚠️ توجه: این یک درخواست تمدید است، لطفاً در رسید خود عبارت "تمدید" را ذکر کنید."""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    
    try:
        await query.edit_message_text(renewal_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        await query.message.reply_text(renewal_text, reply_markup=InlineKeyboardMarkup(keyboard))

# پردازش کد تخفیف
async def process_discount_code(query, product_key):
    user_states[query.from_user.id] = {
        'waiting_for_discount_code': True,
        'product_key': product_key
    }
    
    text = """
🎫 کد تخفیف

لطفاً کد تخفیف خود را وارد کنید:
"""
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    
    try:
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# پردازش کسر از موجودی
async def process_balance_payment(query, product_key, context):
    user_id = query.from_user.id
    user_info = get_user_info(user_id)
    product = PRODUCTS[product_key]
    
    # بررسی موجودی کافی
    if user_info['balance'] < product['price']:
        text = f"""❌ موجودی ناکافی!

💰 موجودی فعلی: {user_info['balance']:,} تومان
💳 قیمت محصول: {product['price']:,} تومان
📉 کمبود: {product['price'] - user_info['balance']:,} تومان

لطفاً ابتدا حساب خود را شارژ کنید."""
        
        keyboard = [
            [InlineKeyboardButton("💰 شارژ حساب", callback_data="charge_account")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # کسر مبلغ از موجودی
    user_info['balance'] -= product['price']
    user_info['orders'] += 1
    save_user_data()
    
    # ارسال درخواست برای مدیران
    purchase_text = f"""📝 درخواست خرید جدید (کسر از موجودی)

👤 کاربر: {query.from_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
👤 نام کاربری: @{query.from_user.username or 'ندارد'}

🛍️ محصول: {product['name']}
💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}

💳 روش پرداخت: کسر از موجودی
✅ مبلغ از موجودی کسر شد"""
    
    # دکمه‌های مدیریت برای مدیران
    admin_keyboard = [
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_purchase_{user_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_purchase_{user_id}")],
        [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")],
        [InlineKeyboardButton("🚫 مسدود", callback_data=f"block_{user_id}"), 
         InlineKeyboardButton("🔓 رفع مسدودی", callback_data=f"unblock_{user_id}")],
        [InlineKeyboardButton("⚠️ اخطار", callback_data=f"warn_{user_id}")]
    ]
    
    # ارسال برای همه مدیران
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id, 
                purchase_text, 
                reply_markup=InlineKeyboardMarkup(admin_keyboard)
            )
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به مدیر {admin_id}: {e}")
    
    # پیام تایید برای کاربر
    success_text = f"""✅ خرید با موفقیت انجام شد!

🛍️ محصول: {product['name']}
💰 مبلغ پرداختی: {product['price']:,} تومان
📱 کد محصول: {product['code']}

💰 موجودی باقیمانده: {user_info['balance']:,} تومان

محصول شما در اسرع وقت برای شما ارسال خواهد شد."""
    
    keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]]
    try:
        await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        await query.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))

# اعمال کد تخفیف جدید
async def apply_discount_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
        
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    if user_id not in user_states or not user_states[user_id].get('waiting_for_discount_code'):
        return
    
    product_key = user_states[user_id]['product_key']
    
    # بررسی وجود کد تخفیف
    if code not in discount_codes:
        await update.message.reply_text(
            "❌ کد تخفیف وارد شده معتبر نیست!\nلطفاً کد صحیح را وارد کنید.",
            reply_markup=main_menu(user_id)
        )
        del user_states[user_id]
        return
    
    discount_info = discount_codes[code]
    discount_category = discount_info.get('category', '')
    
    # بررسی اینکه کد تخفیف برای این محصول قابل اعمال است یا نه
    if not can_apply_discount_to_product(discount_category, product_key):
        await update.message.reply_text(
            f"❌ این کد تخفیف برای محصول {PRODUCTS[product_key]['name']} قابل اعمال نیست!\nاین کد فقط برای بخش {discount_category} قابل استفاده است.",
            reply_markup=main_menu(user_id)
        )
        del user_states[user_id]
        return
    
    # محاسبه تخفیف
    original_price = PRODUCTS[product_key]['price']
    discount_percent = discount_info['discount']
    discount_amount = int((original_price * discount_percent) / 100)
    final_price = original_price - discount_amount
    
    # ذخیره اطلاعات تخفیف برای کاربر
    user_states[user_id] = {
        'waiting_for_receipt': True,
        'product_key': product_key,
        'product_name': PRODUCTS[product_key]['name'],
        'product_code': PRODUCTS[product_key]['code'],
        'amount': final_price,
        'discount_applied': True,
        'discount_code': code,
        'discount_amount': discount_amount,
        'original_price': original_price
    }
    
    card_number = payment_settings.get('card_number', '5859831176852845')
    card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
    
    # ارسال فاکتور جدید
    invoice_text = f"""
✅ کد تخفیف اعمال شد!

📋 فاکتور جدید:
🎯 محصول: {PRODUCTS[product_key]['name']}
💰 قیمت اصلی: {original_price:,} تومان
🎫 کد تخفیف: {code} ({discount_percent}%)
💸 مبلغ تخفیف: {discount_amount:,} تومان
💳 مبلغ قابل پرداخت: {final_price:,} تومان

☑️ ممنون از انتخاب و اعتماد شما
لطفا مبلغ {final_price:,} تومان به کارت زیر واریز کنید

💳 شماره کارت:
{card_number}
بنام {card_holder}

لطفاً رسید و عکس کسر موجودی با کد محصول رو بفرستید ✅
📱 کد محصول: {PRODUCTS[product_key]['code']}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
    await update.message.reply_text(invoice_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # آمارگیری استفاده از کد تخفیف
    user_stats['discount_codes_used'] += 1
    save_user_data()

# مدیریت دکمه‌ها
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
        
    query = update.callback_query
    user_id = query.from_user.id
    
    # بررسی آنتی اسپم
    if not check_anti_spam(user_id):
        await query.answer("⚠️ شما خیلی سریع کلیک می‌کنید. لطفاً کمی صبر کنید.")
        return
        
    await query.answer()
    
    # اضافه کردن کاربر به آمار فعال امروز
    user_stats['active_users_today'].add(user_id)
    
    # بررسی مسدود بودن کاربر
    if user_id in user_blocked and user_id not in ADMIN_IDS:
        await query.edit_message_text("🚫 شما از استفاده از این ربات محروم شده‌اید.")
        return

    # منوی اصلی
    if query.data == "main_menu":
        await query.edit_message_text(
            "🏠 منوی اصلی:\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=main_menu(user_id)
        )

    # بررسی عضویت چنل
    elif query.data == "check_membership":
        is_member = await check_channel_membership(context.bot, user_id)
        if is_member:
            await query.edit_message_text(
                f"✅ عالی! شما عضو چنل هستید.\n\n🌟 سلام {query.from_user.first_name} عزیز!\n\nبه ربات خدمات ما خوش اومدی 🎉\n\nاز منوی زیر می‌تونی استفاده کنی:",
                reply_markup=main_menu(user_id)
            )
        else:
            await query.answer("❌ شما هنوز عضو چنل نشده‌اید!", show_alert=True)

    # منوی آموزش جدید
    elif query.data == "tutorial":
        keyboard = [
            [InlineKeyboardButton("📱 Android", callback_data="tutorial_android")],
            [InlineKeyboardButton("🍎 iOS", callback_data="tutorial_ios")],
            [InlineKeyboardButton("💻 PC", callback_data="tutorial_pc")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "📚 آموزش:\n\nلطفاً پلتفرم مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("tutorial_"):
        platform = query.data.replace("tutorial_", "")
        text_key = f"tutorial_{platform}"
        text_content = editable_texts.get(text_key, "درحال اپدیت")
        
        platform_name = {"android": "📱 Android", "ios": "🍎 iOS", "pc": "💻 PC"}.get(platform, platform)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="tutorial")]]
        await query.edit_message_text(
            f"{platform_name} آموزش:\n\n{text_content}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # نمایش قوانین
    elif query.data == "show_rules":
        rules_text = editable_texts.get('rules_text', 'درحال اپدیت')
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        try:
            await query.edit_message_text(
                f"📜 قوانین:\n\n{rules_text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                f"📜 قوانین:\n\n{rules_text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # درخواست تمدید
    elif query.data == "extension_request":
        text = """🔄 تمدید محصولات

💡 برای تمدید محصولات خود:

1️⃣ کد تمدید خود را از مالک دریافت کنید
2️⃣ کد تمدید را در این بخش وارد کنید  
3️⃣ فاکتور تمدید برای شما ارسال خواهد شد

🔗 لطفاً کد تمدید خود را وارد کنید:"""
        
        # ذخیره وضعیت کاربر
        user_states[user_id] = {
            'waiting_for_extension_code': True
        }
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # خرید محصولات
    elif query.data == "buy":
        keyboard = [
            [InlineKeyboardButton("📱 اندروید", callback_data="buy_android")],
            [InlineKeyboardButton("🍎 آیفون", callback_data="buy_ios")],
            [InlineKeyboardButton("💻 پیسی", callback_data="buy_pc")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text(
                "🛒 خرید محصولات:\n\nلطفاً پلتفرم مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🛒 خرید محصولات:\n\nلطفاً پلتفرم مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "buy_android":
        keyboard = [
            [InlineKeyboardButton("⚙️ کانفیگ", callback_data="android_config")],
            [InlineKeyboardButton("🎮 چیت", callback_data="android_cheat")],
            [InlineKeyboardButton("🌐 DNS", callback_data="android_dns")],
            [InlineKeyboardButton("🔒 وایرگاد", callback_data="android_wireguard")],
            [InlineKeyboardButton("🏠 هاست", callback_data="android_host")],
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="android_fixlag")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")]
        ]
        try:
            await query.edit_message_text(
                "📱 محصولات اندروید:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "📱 محصولات اندروید:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # اضافه کردن handler برای چیت اندروید
    elif query.data == "android_cheat":
        cheat_text = editable_texts.get('android_cheat', 'درحال اپدیت')
        
        if cheat_text == 'درحال اپدیت':
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]]
            try:
                await query.edit_message_text(
                    f"🎮 چیت اندروید:\n\n{cheat_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                await query.message.reply_text(
                    f"🎮 چیت اندروید:\n\n{cheat_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # اگر محتوای کاملی داریم، دکمه خرید هم بزاریم
            keyboard = [
                [InlineKeyboardButton("💳 خرید", callback_data="show_android_cheat_product")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
            ]
            try:
                await query.edit_message_text(
                    f"🎮 چیت اندروید:\n\n{cheat_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                await query.message.reply_text(
                    f"🎮 چیت اندروید:\n\n{cheat_text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    elif query.data == "show_android_cheat_product":
        product = PRODUCTS["android_cheat"]
        text = f"""🎮 چیت اندروید

📱 نام محصول: {product['name']}
💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}

✨ ویژگی‌ها:
{editable_texts.get('android_cheat', 'درحال اپدیت')}"""
        
        try:
            await query.edit_message_text(
                text, 
                reply_markup=create_purchase_buttons("android_cheat", "buy_android", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text, 
                reply_markup=create_purchase_buttons("android_cheat", "buy_android", user_id)
            )

    # Handler های محصولات اندروید
    elif query.data == "android_config":
        user_states[user_id] = {'platform_context': 'android'}
        keyboard = [
            [InlineKeyboardButton("🥉 کانفیگ بیسیک", callback_data="android_config_basic")],
            [InlineKeyboardButton("⭐ کانفیگ کاستوم", callback_data="android_config_custom")],
            [InlineKeyboardButton("👑 کانفیگ خصوصی", callback_data="android_config_private")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "⚙️ کانفیگ اندروید:\n\nلطفاً نوع کانفیگ مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "⚙️ کانفیگ اندروید:\n\nلطفاً نوع کانفیگ مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_dns":
        user_states[user_id] = {'platform_context': 'android'}
        keyboard = [
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="android_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="android_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="android_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="android_dns_exclusive")],
            [InlineKeyboardButton("🏆 DNS لجندری", callback_data="android_dns_legendary")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🌐 DNS اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🌐 DNS اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_wireguard":
        user_states[user_id] = {'platform_context': 'android'}
        keyboard = [
            [InlineKeyboardButton("1️⃣ تک لوکیشن", callback_data="android_wireguard_single")],
            [InlineKeyboardButton("2️⃣ دو لوکیشن", callback_data="android_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ سه لوکیشن", callback_data="android_wireguard_triple")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🔒 وایرگاد اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🔒 وایرگاد اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_host":
        user_states[user_id] = {'platform_context': 'android'}
        keyboard = [
            [InlineKeyboardButton("🥉 هاست بیسیک", callback_data="android_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="android_host_vip")],
            [InlineKeyboardButton("🔥 هاست کاستوم", callback_data="android_host_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🏠 هاست اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🏠 هاست اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_fixlag":
        user_states[user_id] = {'platform_context': 'android'}
        keyboard = [
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="android_fixlag_basic")],
            [InlineKeyboardButton("📈 افزایش FPS", callback_data="android_fixlag_fps")],
            [InlineKeyboardButton("⚡ FPS + کاهش لگ", callback_data="android_fixlag_fps_plus")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🔧 فیکس لگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🔧 فیکس لگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Handler های محصولات خاص اندروید - Config
    elif query.data == "android_config_basic":
        text = f"""⚙️ کانفیگ بیسیک اندروید

📱 نام محصول: {PRODUCTS['config_basic']['name']}
💰 قیمت: {PRODUCTS['config_basic']['price']:,} تومان
📱 کد محصول: {PRODUCTS['config_basic']['code']}

✨ ویژگی‌ها:
• کیفیت عالی برای گیمینگ
• سرعت بالا و پینگ کم
• پشتیبانی 24 ساعته"""
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=create_purchase_buttons("config_basic", "android_config", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=create_purchase_buttons("config_basic", "android_config", user_id)
            )

    elif query.data == "android_config_custom":
        text = f"""⚙️ کانفیگ کاستوم اندروید

📱 نام محصول: {PRODUCTS['config_custom']['name']}
💰 قیمت: {PRODUCTS['config_custom']['price']:,} تومان
📱 کد محصول: {PRODUCTS['config_custom']['code']}

✨ ویژگی‌ها:
• کانفیگ اختصاصی
• بهینه‌سازی شخصی
• پشتیبانی VIP"""
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=create_purchase_buttons("config_custom", "android_config", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=create_purchase_buttons("config_custom", "android_config", user_id)
            )

    elif query.data == "android_config_private":
        text = f"""⚙️ کانفیگ خصوصی اندروید

📱 نام محصول: {PRODUCTS['config_private']['name']}
💰 قیمت: {PRODUCTS['config_private']['price']:,} تومان
📱 کد محصول: {PRODUCTS['config_private']['code']}

✨ ویژگی‌ها:
• کانفیگ کاملاً اختصاصی
• بالاترین کیفیت
• پشتیبانی فوری"""
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=create_purchase_buttons("config_private", "android_config", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=create_purchase_buttons("config_private", "android_config", user_id)
            )

    # Handler های DNS اندروید
    elif query.data == "android_dns_bronze":
        text = f"""🌐 DNS برنز اندروید

📱 نام محصول: {PRODUCTS['dns_bronze']['name']}
💰 قیمت: {PRODUCTS['dns_bronze']['price']:,} تومان
📱 کد محصول: {PRODUCTS['dns_bronze']['code']}

✨ ویژگی‌ها:
• سرعت مناسب
• قیمت اقتصادی
• مناسب استفاده عمومی"""
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=create_purchase_buttons("dns_bronze", "android_dns", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=create_purchase_buttons("dns_bronze", "android_dns", user_id)
            )

    elif query.data == "android_dns_platinum":
        text = f"""🌐 DNS پلاتینیوم اندروید

📱 نام محصول: {PRODUCTS['dns_platinum']['name']}
💰 قیمت: {PRODUCTS['dns_platinum']['price']:,} تومان
📱 کد محصول: {PRODUCTS['dns_platinum']['code']}

✨ ویژگی‌ها:
• سرعت بالا
• مناسب گیمینگ
• پایداری عالی"""
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=create_purchase_buttons("dns_platinum", "android_dns", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=create_purchase_buttons("dns_platinum", "android_dns", user_id)
            )

    elif query.data == "android_dns_elite":
        text = f"""🌐 DNS آلیت اندروید

📱 نام محصول: {PRODUCTS['dns_elite']['name']}
💰 قیمت: {PRODUCTS['dns_elite']['price']:,} تومان
📱 کد محصول: {PRODUCTS['dns_elite']['code']}

✨ ویژگی‌ها:
• کیفیت پریمیوم
• بهترین سرعت
• پشتیبانی اولویت دار"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("dns_elite", "android_dns", user_id)
        )

    elif query.data == "android_dns_exclusive":
        text = f"""🌐 DNS اکسکلوسیو اندروید

📱 نام محصول: {PRODUCTS['dns_exclusive']['name']}
💰 قیمت: {PRODUCTS['dns_exclusive']['price']:,} تومان
📱 کد محصول: {PRODUCTS['dns_exclusive']['code']}

✨ ویژگی‌ها:
• DNS اختصاصی
• سرعت فوق‌العاده
• بدون محدودیت"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("dns_exclusive", "android_dns", user_id)
        )

    elif query.data == "android_dns_legendary":
        text = f"""🌐 DNS لجندری اندروید

📱 نام محصول: {PRODUCTS['dns_legendary']['name']}
💰 قیمت: {PRODUCTS['dns_legendary']['price']:,} تومان
📱 کد محصول: {PRODUCTS['dns_legendary']['code']}

✨ ویژگی‌ها:
• بالاترین کیفیت
• سرعت نامحدود
• پشتیبانی VIP"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("dns_legendary", "android_dns", user_id)
        )

    # Handler های WireGuard اندروید
    elif query.data == "android_wireguard_single":
        text = f"""🔒 وایرگاد تک لوکیشن اندروید

📱 نام محصول: {PRODUCTS['wireguard_single']['name']}
💰 قیمت: {PRODUCTS['wireguard_single']['price']:,} تومان
📱 کد محصول: {PRODUCTS['wireguard_single']['code']}

✨ ویژگی‌ها:
• یک لوکیشن اختصاصی
• سرعت عالی
• امنیت بالا"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("wireguard_single", "android_wireguard", user_id)
        )

    elif query.data == "android_wireguard_dual":
        text = f"""🔒 وایرگاد دو لوکیشن اندروید

📱 نام محصول: {PRODUCTS['wireguard_dual']['name']}
💰 قیمت: {PRODUCTS['wireguard_dual']['price']:,} تومان
📱 کد محصول: {PRODUCTS['wireguard_dual']['code']}

✨ ویژگی‌ها:
• دو لوکیشن مختلف
• انتخاب سرور
• پایداری بیشتر"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("wireguard_dual", "android_wireguard", user_id)
        )

    elif query.data == "android_wireguard_triple":
        text = f"""🔒 وایرگاد سه لوکیشن اندروید

📱 نام محصول: {PRODUCTS['wireguard_triple']['name']}
💰 قیمت: {PRODUCTS['wireguard_triple']['price']:,} تومان
📱 کد محصول: {PRODUCTS['wireguard_triple']['code']}

✨ ویژگی‌ها:
• سه لوکیشن متنوع
• گزینه‌های بیشتر
• حداکثر انعطاف‌پذیری"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("wireguard_triple", "android_wireguard", user_id)
        )

    # Handler های Host اندروید
    elif query.data == "android_host_basic":
        text = f"""🏠 هاست بیسیک اندروید

📱 نام محصول: {PRODUCTS['host_basic']['name']}
💰 قیمت: {PRODUCTS['host_basic']['price']:,} تومان
📱 کد محصول: {PRODUCTS['host_basic']['code']}

✨ ویژگی‌ها:
• هاست پایه
• مناسب شروع کار
• پشتیبانی استندارد"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("host_basic", "android_host", user_id)
        )

    elif query.data == "android_host_vip":
        text = f"""🏠 هاست VIP اندروید

📱 نام محصول: {PRODUCTS['host_vip']['name']}
💰 قیمت: {PRODUCTS['host_vip']['price']:,} تومان
📱 کد محصول: {PRODUCTS['host_vip']['code']}

✨ ویژگی‌ها:
• هاست VIP
• کیفیت بالا
• پشتیبانی اولویت‌دار"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("host_vip", "android_host", user_id)
        )

    elif query.data == "android_host_custom":
        text = f"""🏠 هاست کاستوم اندروید

📱 نام محصول: {PRODUCTS['host_custom']['name']}
💰 قیمت: {PRODUCTS['host_custom']['price']:,} تومان
📱 کد محصول: {PRODUCTS['host_custom']['code']}

✨ ویژگی‌ها:
• هاست اختصاصی
• تنظیمات دلخواه
• عملکرد بهینه"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("host_custom", "android_host", user_id)
        )

    # Handler های FixLag اندروید
    elif query.data == "android_fixlag_basic":
        text = f"""🔧 فیکس لگ اندروید

📱 نام محصول: {PRODUCTS['fixlag_basic']['name']}
💰 قیمت: {PRODUCTS['fixlag_basic']['price']:,} تومان
📱 کد محصول: {PRODUCTS['fixlag_basic']['code']}
⏱️ مدت زمان: {PRODUCTS['fixlag_basic']['duration']}

✨ ویژگی‌ها:
• کاهش لگ در بازی
• بهبود پینگ
• تجربه بازی بهتر"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("fixlag_basic", "android_fixlag", user_id)
        )

    elif query.data == "android_fixlag_fps":
        text = f"""🔧 افزایش FPS اندروید

📱 نام محصول: {PRODUCTS['fixlag_fps']['name']}
💰 قیمت: {PRODUCTS['fixlag_fps']['price']:,} تومان
📱 کد محصول: {PRODUCTS['fixlag_fps']['code']}
⏱️ مدت زمان: {PRODUCTS['fixlag_fps']['duration']}

✨ ویژگی‌ها:
• افزایش نرخ فریم
• بهبود عملکرد
• بازی روان‌تر"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("fixlag_fps", "android_fixlag", user_id)
        )

    elif query.data == "android_fixlag_fps_plus":
        text = f"""🔧 FPS + کاهش لگ اندروید

📱 نام محصول: {PRODUCTS['fixlag_fps_plus']['name']}
💰 قیمت: {PRODUCTS['fixlag_fps_plus']['price']:,} تومان
📱 کد محصول: {PRODUCTS['fixlag_fps_plus']['code']}
⏱️ مدت زمان: {PRODUCTS['fixlag_fps_plus']['duration']}

✨ ویژگی‌ها:
• کاهش لگ + افزایش FPS
• بهترین تجربه
• عملکرد حرفه‌ای"""
        
        await query.edit_message_text(
            text,
            reply_markup=create_purchase_buttons("fixlag_fps_plus", "android_fixlag", user_id)
        )

    # پنل مدیریت
    elif query.data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        try:
            await query.edit_message_text(
                "👨‍💼 پنل مدیریت:\n\nلطفاً بخش مورد نظر را انتخاب کنید:",
                reply_markup=admin_panel_menu()
            )
        except Exception:
            await query.message.reply_text(
                "👨‍💼 پنل مدیریت:\n\nلطفاً بخش مورد نظر را انتخاب کنید:",
                reply_markup=admin_panel_menu()
            )

    # پنل مدیریت تمدید
    elif query.data == "admin_extension":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        # محاسبه آمار تمدید
        total_extensions = sum(1 for uid, udata in user_data.items() 
                              if udata.get('extensions', 0) > 0)
        
        text = f"""🔄 پنل مدیریت تمدید

📊 آمار کلی:
👥 کل کاربران: {len(user_data)}
🔄 کاربران با تمدید: {total_extensions}
📝 درخواست‌های تمدید امروز: 0

⚙️ مدیریت:"""

        keyboard = [
            [InlineKeyboardButton("📋 نمایش همه درخواست‌ها", callback_data="admin_extension_requests")],
            [InlineKeyboardButton("🎫 ساخت کد تمدید", callback_data="admin_create_extension_code")],
            [InlineKeyboardButton("📊 آمار تمدید", callback_data="admin_extension_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش عضویت اجباری
    elif query.data == "admin_membership":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        current_status = "فعال" if editable_texts.get('mandatory_membership', True) else "غیرفعال"
        current_channel = CHANNEL_USERNAME
        additional_count = len(ADDITIONAL_CHANNELS)
        
        text = f"""🔗 مدیریت عضویت اجباری

📊 وضعیت فعلی: {current_status}
📺 چنل اصلی: {current_channel}
📋 کانال‌های اضافی: {additional_count} کانال

تنظیمات:"""
        
        keyboard = [
            [InlineKeyboardButton("✅ فعال کردن" if not editable_texts.get('mandatory_membership', True) 
                                else "❌ غیرفعال کردن", callback_data="toggle_membership")],
            [InlineKeyboardButton("📺 تغییر چنل اصلی", callback_data="change_channel")],
            [InlineKeyboardButton("➕ اضافه کردن کانال", callback_data="add_channel")],
            [InlineKeyboardButton("📋 مشاهده کانال‌ها", callback_data="view_channels")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_membership":
        if user_id not in ADMIN_IDS:
            return
        
        editable_texts['mandatory_membership'] = not editable_texts.get('mandatory_membership', True)
        save_user_data()
        
        status = "فعال" if editable_texts['mandatory_membership'] else "غیرفعال"
        await query.answer(f"✅ عضویت اجباری {status} شد!", show_alert=True)
        
        # بازگشت به منوی عضویت اجباری
        await query.edit_message_text(
            f"🔗 عضویت اجباری {status} شد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]])
        )

    elif query.data == "add_channel":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_new_channel': True}
        text = """➕ اضافه کردن کانال جدید

لطفاً نام کانال (یا لینک) را ارسال کنید:

مثال:
@channel_name
یا
https://t.me/channel_name

📌 توجه: کانال باید عمومی باشد تا ربات بتواند عضویت کاربران را بررسی کند."""
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_membership")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "view_channels":
        if user_id not in ADMIN_IDS:
            return
        
        text = f"""📋 لیست کانال‌های اجباری

📺 کانال اصلی: {CHANNEL_USERNAME}

"""
        
        if ADDITIONAL_CHANNELS:
            text += "📋 کانال‌های اضافی:\n"
            for i, channel in enumerate(ADDITIONAL_CHANNELS, 1):
                text += f"{i}. {channel}\n"
            
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف کانال", callback_data="remove_channel")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]
            ]
        else:
            text += "📋 کانال اضافی ثبت نشده است."
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "remove_channel":
        if user_id not in ADMIN_IDS:
            return
        
        if not ADDITIONAL_CHANNELS:
            await query.answer("❌ کانال اضافی برای حذف وجود ندارد!", show_alert=True)
            return
        
        user_states[user_id] = {'waiting_for_channel_to_remove': True}
        text = """🗑️ حذف کانال

لیست کانال‌های اضافی:
"""
        
        for i, channel in enumerate(ADDITIONAL_CHANNELS, 1):
            text += f"{i}. {channel}\n"
        
        text += "\nلطفاً شماره کانال مورد نظر برای حذف را ارسال کنید:"
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="view_channels")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش قوانین
    elif query.data == "admin_rules":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        current_rules = editable_texts.get('rules_text', 'درحال اپدیت')
        text = f"""📜 مدیریت قوانین

📝 متن فعلی قوانین:
{current_rules[:200]}{'...' if len(current_rules) > 200 else ''}

تنظیمات:"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ ویرایش قوانین", callback_data="edit_rules")],
            [InlineKeyboardButton("👀 مشاهده کامل", callback_data="view_full_rules")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "edit_rules":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_rules_text': True}
        text = """✏️ ویرایش قوانین

لطفاً متن جدید قوانین را ارسال کنید:

💡 این متن در بخش قوانین و همچنین در صفحات خرید محصولات نمایش داده خواهد شد."""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_rules")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "view_full_rules":
        if user_id not in ADMIN_IDS:
            return
        
        full_rules = editable_texts.get('rules_text', 'درحال اپدیت')
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_rules")]]
        await query.edit_message_text(
            f"📜 قوانین کامل:\n\n{full_rules}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # بخش آنتی اسپم
    elif query.data == "admin_antispam":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        status = "فعال" if editable_texts.get('anti_spam_enabled', False) else "غیرفعال"
        limit = editable_texts.get('anti_spam_limit', 5)
        
        text = f"""🛡️ مدیریت آنتی اسپم

📊 وضعیت: {status}
⏱️ حد مجاز: {limit} پیام در دقیقه

تنظیمات:"""
        
        keyboard = [
            [InlineKeyboardButton("✅ فعال کردن" if not editable_texts.get('anti_spam_enabled', False) 
                                else "❌ غیرفعال کردن", callback_data="toggle_antispam")],
            [InlineKeyboardButton("⚙️ تنظیم حد مجاز", callback_data="set_spam_limit")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_antispam":
        if user_id not in ADMIN_IDS:
            return
        
        editable_texts['anti_spam_enabled'] = not editable_texts.get('anti_spam_enabled', False)
        save_user_data()
        
        status = "فعال" if editable_texts['anti_spam_enabled'] else "غیرفعال"
        await query.answer(f"✅ آنتی اسپم {status} شد!", show_alert=True)
        
        # بازگشت به منوی آنتی اسپم
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_antispam")]]
        await query.edit_message_text(
            f"🛡️ آنتی اسپم {status} شد!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # بخش متن ربات
    elif query.data == "admin_texts":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        text = """📝 مدیریت متن‌های ربات

متن‌های قابل ویرایش:"""
        
        keyboard = [
            [InlineKeyboardButton("📱 آموزش Android", callback_data="edit_text_tutorial_android")],
            [InlineKeyboardButton("🍎 آموزش iOS", callback_data="edit_text_tutorial_ios")],
            [InlineKeyboardButton("💻 آموزش PC", callback_data="edit_text_tutorial_pc")],
            [InlineKeyboardButton("🎮 چیت Android", callback_data="edit_text_android_cheat")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("edit_text_"):
        if user_id not in ADMIN_IDS:
            return
        
        text_key = query.data.replace("edit_text_", "")
        current_text = editable_texts.get(text_key, 'درحال اپدیت')
        
        user_states[user_id] = {'waiting_for_text_edit': True, 'text_key': text_key}
        
        text_names = {
            'tutorial_android': 'آموزش Android',
            'tutorial_ios': 'آموزش iOS', 
            'tutorial_pc': 'آموزش PC',
            'android_cheat': 'چیت Android'
        }
        text_name = text_names.get(text_key, text_key)
        
        text = f"""✏️ ویرایش {text_name}

📝 متن فعلی:
{current_text[:300]}{'...' if len(current_text) > 300 else ''}

لطفاً متن جدید را ارسال کنید:"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_texts")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش آمار کلی
    elif query.data == "admin_stats":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        total_users = len(user_stats['total_users'])
        active_today = len(user_stats['active_users_today'])
        total_revenue = user_stats['total_revenue']
        successful_purchases = user_stats['successful_purchases']
        receipts_submitted = user_stats['receipts_submitted']
        blocked_users = len(user_blocked)
        discount_codes_used = user_stats['discount_codes_used']
        
        text = f"""📊 آمار کلی ربات

👥 کل کاربران: {total_users:,} نفر
🟢 کاربران فعال امروز: {active_today:,} نفر
🚫 کاربران مسدود: {blocked_users:,} نفر

💰 کل درآمد: {total_revenue:,} تومان
✅ خریدهای موفق: {successful_purchases:,} عدد
📋 رسیدهای ارسالی: {receipts_submitted:,} عدد
🎫 کدهای تخفیف استفاده شده: {discount_codes_used:,} عدد

آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_stats")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش گزارش فروش
    elif query.data == "admin_sales":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        total_revenue = user_stats['total_revenue']
        successful_purchases = user_stats['successful_purchases']
        avg_order_value = total_revenue / successful_purchases if successful_purchases > 0 else 0
        
        text = f"""💰 گزارش فروش

📊 خلاصه فروش:
💵 کل درآمد: {total_revenue:,} تومان
🛒 تعداد فروش: {successful_purchases:,} عدد
📈 میانگین هر فروش: {avg_order_value:,.0f} تومان

🏆 محبوب‌ترین محصولات:"""
        
        # اضافه کردن آمار محصولات
        top_products = sorted(
            [(k, v['purchases'], v['revenue']) for k, v in product_stats.items() if v['purchases'] > 0],
            key=lambda x: x[2], reverse=True
        )[:5]
        
        for i, (product_key, purchases, revenue) in enumerate(top_products, 1):
            product_name = PRODUCTS.get(product_key, {}).get('name', product_key)
            text += f"\n{i}. {product_name}: {purchases} فروش - {revenue:,} تومان"
        
        keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_sales")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش رسیدهای ارسالی
    elif query.data == "admin_receipts":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        receipts_submitted = user_stats['receipts_submitted']
        successful_purchases = user_stats['successful_purchases']
        pending_receipts = receipts_submitted - successful_purchases
        
        text = f"""📋 مدیریت رسیدها

📊 آمار رسیدها:
📥 کل رسیدهای ارسالی: {receipts_submitted:,} عدد
✅ رسیدهای تایید شده: {successful_purchases:,} عدد
⏳ رسیدهای در انتظار: {pending_receipts:,} عدد

💡 رسیدهای جدید در پیام‌های خصوصی ربات نمایش داده می‌شوند."""
        
        keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_receipts")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش آمار محصولات
    elif query.data == "admin_products":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        text = "📈 آمار محصولات:\n\n"
        
        # گروه‌بندی محصولات
        categories = {
            "کانفیگ": ["config_basic", "config_custom", "config_private", "pc_config_basic", "pc_config_vvip", "pc_config_custom", "pc_config_private"],
            "DNS": ["dns_bronze", "dns_platinum", "dns_elite", "dns_exclusive", "dns_legendary"],
            "چیت": ["android_cheat", "ios_cheat"],
            "وایرگاد": ["wireguard_single", "wireguard_dual", "wireguard_triple"],
            "هاست": ["host_basic", "host_vip", "host_custom"],
            "سایت": ["site_premium", "site_normal"],
            "فیکس لگ": ["fixlag_basic", "fixlag_fps", "fixlag_fps_plus"]
        }
        
        for category, products in categories.items():
            text += f"\n🔸 {category}:\n"
            for product_key in products:
                if product_key in product_stats:
                    stats = product_stats[product_key]
                    name = PRODUCTS.get(product_key, {}).get('name', product_key)
                    text += f"• {name}: {stats['purchases']} فروش - {stats['revenue']:,} تومان\n"
        
        keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_products")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))  # محدود کردن طول پیام
        except Exception:
            await query.message.reply_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش پنل کد تخفیف جدید
    elif query.data == "discount_codes_panel":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        text = f"""🎫 پنل کدهای تخفیف

📊 آمار:
🎟️ تعداد کدهای فعال: {len(discount_codes)}
📊 استفاده شده: {user_stats['discount_codes_used']}

کدهای فعال:"""
        
        if discount_codes:
            for i, (code, info) in enumerate(list(discount_codes.items())[:5], 1):  # نمایش 5 کد اول با شماره
                category = info.get('category', 'نامشخص')
                text += f"\n{i}. {code}: {info['discount']}% - {category}"
            
            if len(discount_codes) > 5:
                text += f"\n... و {len(discount_codes) - 5} کد دیگر"
        else:
            text += "\n\n❌ هیچ کد تخفیفی تعریف نشده است."
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن کد تخفیف", callback_data="add_new_discount_code")],
            [InlineKeyboardButton("🗑️ حذف کد تخفیف", callback_data="remove_discount_code_new")],
            [InlineKeyboardButton("📋 مشاهده همه کدها", callback_data="view_all_discounts_new")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_new_discount_code":
        if user_id not in ADMIN_IDS:
            return
        
        text = """➕ افزودن کد تخفیف جدید

📋 مرحله 1: انتخاب بخش محصولات
لطفاً بخش محصولاتی که کد تخفیف برای آن اعمال شود را انتخاب کنید:"""
        
        keyboard = [
            [InlineKeyboardButton("⚙️ کانفیگ بیسیک", callback_data="new_discount_config_basic")],
            [InlineKeyboardButton("⭐ کانفیگ کاستوم", callback_data="new_discount_config_custom")],
            [InlineKeyboardButton("💎 کانفیگ خصوصی", callback_data="new_discount_config_private")],
            [InlineKeyboardButton("🎮 چیت اندروید", callback_data="new_discount_android_cheat")],
            [InlineKeyboardButton("🍎 چیت آیفون", callback_data="new_discount_ios_cheat")],
            [InlineKeyboardButton("💻 کانفیگ PC بیسیک", callback_data="new_discount_pc_config_basic")],
            [InlineKeyboardButton("👑 کانفیگ PC VVIP", callback_data="new_discount_pc_config_vvip")],
            [InlineKeyboardButton("⭐ کانفیگ PC کاستوم", callback_data="new_discount_pc_config_custom")],
            [InlineKeyboardButton("💎 کانفیگ PC خصوصی", callback_data="new_discount_pc_config_private")],
            [InlineKeyboardButton("🏠 هاست بیسیک", callback_data="new_discount_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="new_discount_host_vip")],
            [InlineKeyboardButton("⭐ هاست کاستوم", callback_data="new_discount_host_custom")],
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="new_discount_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="new_discount_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="new_discount_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="new_discount_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="new_discount_dns_legendary")],
            [InlineKeyboardButton("1️⃣ وایرگاد تک لوکیشن", callback_data="new_discount_wireguard_single")],
            [InlineKeyboardButton("2️⃣ وایرگاد دو لوکیشن", callback_data="new_discount_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ وایرگاد سه لوکیشن", callback_data="new_discount_wireguard_triple")],
            [InlineKeyboardButton("🌐 سایت نسخه ویژه", callback_data="new_discount_site_premium")],
            [InlineKeyboardButton("🌐 سایت نسخه عادی", callback_data="new_discount_site_normal")],
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="new_discount_fixlag_basic")],
            [InlineKeyboardButton("📈 کانفیگ افزایش FPS", callback_data="new_discount_fixlag_fps")],
            [InlineKeyboardButton("⚡ کانفیگ FPS + کاهش لگ", callback_data="new_discount_fixlag_fps_plus")],
            [InlineKeyboardButton("🌐 سایت نسخه ویژه", callback_data="new_discount_site_premium")],
            [InlineKeyboardButton("🌐 سایت نسخه عادی", callback_data="new_discount_site_normal")],
            [InlineKeyboardButton("🌟 همه محصولات", callback_data="new_discount_all")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "remove_discount_code_new":
        if user_id not in ADMIN_IDS:
            return
        
        if not discount_codes:
            await query.answer("❌ هیچ کد تخفیفی برای حذف وجود ندارد!", show_alert=True)
            return
        
        text = """🗑️ حذف کد تخفیف

📋 کدهای تخفیف فعال:

"""
        
        codes_list = list(discount_codes.items())
        for i, (code, info) in enumerate(codes_list, 1):
            category = info.get('category', 'نامشخص')
            text += f"{i}. {code} - {info['discount']}% - {category}\n"
        
        text += "\nلطفاً شماره کد تخفیف مورد نظر برای حذف را ارسال کنید:"
        
        user_states[user_id] = {
            'waiting_for_new_discount_removal': True,
            'available_codes': codes_list
        }
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="discount_codes_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "view_all_discounts_new":
        if user_id not in ADMIN_IDS:
            return
        
        if not discount_codes:
            text = "❌ هیچ کد تخفیفی تعریف نشده است."
        else:
            text = f"📋 همه کدهای تخفیف ({len(discount_codes)} کد):\n\n"
            
            for i, (code, info) in enumerate(discount_codes.items(), 1):
                category = info.get('category', 'نامشخص')
                text += f"{i}. 🎫 {code}\n"
                text += f"   📊 تخفیف: {info['discount']}%\n"
                text += f"   📦 بخش: {category}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]]
        try:
            await query.edit_message_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))  # محدود کردن طول پیام
        except Exception:
            await query.message.reply_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))

    # Handlers جدید برای category selection
    elif query.data.startswith("new_discount_"):
        if user_id not in ADMIN_IDS:
            return
        
        category_map = {
            "new_discount_config_basic": "کانفیگ بیسیک",
            "new_discount_config_custom": "کانفیگ کاستوم", 
            "new_discount_config_private": "کانفیگ خصوصی",
            "new_discount_android_cheat": "چیت اندروید",
            "new_discount_ios_cheat": "چیت آیفون",
            "new_discount_pc_config_basic": "کانفیگ PC بیسیک",
            "new_discount_pc_config_vvip": "کانفیگ PC VVIP",
            "new_discount_pc_config_custom": "کانفیگ PC کاستوم",
            "new_discount_pc_config_private": "کانفیگ PC خصوصی",
            "new_discount_host_basic": "هاست بیسیک",
            "new_discount_host_vip": "هاست VIP",
            "new_discount_host_custom": "هاست کاستوم",
            "new_discount_dns_bronze": "DNS برنز",
            "new_discount_dns_platinum": "DNS پلاتینیوم",
            "new_discount_dns_elite": "DNS آلیت",
            "new_discount_dns_exclusive": "DNS اکسکلوسیو",
            "new_discount_dns_legendary": "DNS لجندری",
            "new_discount_wireguard_single": "وایرگاد تک لوکیشن",
            "new_discount_wireguard_dual": "وایرگاد دو لوکیشن",
            "new_discount_wireguard_triple": "وایرگاد سه لوکیشن",
            "new_discount_site_premium": "سایت نسخه ویژه",
            "new_discount_site_normal": "سایت نسخه عادی",
            "new_discount_fixlag_basic": "فیکس لگ",
            "new_discount_fixlag_fps": "کانفیگ افزایش FPS",
            "new_discount_fixlag_fps_plus": "کانفیگ FPS + کاهش لگ",
            "new_discount_site_premium": "سایت نسخه ویژه",
            "new_discount_site_normal": "سایت نسخه عادی",
            "new_discount_all": "همه محصولات"
        }
        
        selected_category = category_map.get(query.data, "نامشخص")
        
        user_states[user_id] = {
            'waiting_for_new_discount_code': True,
            'discount_category': selected_category
        }
        
        text = f"""➕ افزودن کد تخفیف جدید

✅ بخش انتخابی: {selected_category}

📋 مرحله 2: وارد کردن کد تخفیف
لطفاً کد تخفیف را وارد کنید:

💡 نکته: درصد تخفیف به صورت خودکار از اعداد آخر کد استخراج می‌شود
📝 مثال: KIAYT10 → 10% تخفیف, ali20 → 20% تخفیف"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="add_new_discount_code")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش پیام همگانی
    elif query.data == "admin_broadcast":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        total_users = len(user_stats['total_users'])
        text = f"""📢 پیام همگانی

👥 تعداد کاربران: {total_users:,} نفر

⚠️ توجه:
• پیام به همه کاربران ارسال خواهد شد
• ارسال پیام ممکن است چند دقیقه طول بکشد
• پیام‌های خیلی طولانی ممکن است کامل ارسال نشوند

لطفاً متن پیام همگانی را وارد کنید:"""
        
        user_states[user_id] = {'waiting_for_broadcast_message': True}
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش مدیریت ویدیو سایت
    elif query.data == "admin_site_video":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        video_status = "✅ آپلود شده" if SITE_VIDEO_FILE_ID else "❌ آپلود نشده"
        text = f"""🎥 مدیریت ویدیو سایت

📊 وضعیت: {video_status}

💡 راهنمای استفاده:
• ویدیو را در همین چت ارسال کنید
• ویدیو به صورت خودکار ذخیره می‌شود
• ویدیو در بخش سایت نمایش داده خواهد شد

لطفاً ویدیو جدید را ارسال کنید:"""
        
        user_states[user_id] = {'waiting_for_site_video': True}
        keyboard = [[InlineKeyboardButton("🗑️ حذف ویدیو فعلی", callback_data="delete_site_video")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش مدیریت ویدیو محصولات
    elif query.data == "admin_product_videos":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        uploaded_count = len([k for k, v in PRODUCT_VIDEOS.items() if v])
        total_products = len(PRODUCTS)
        
        text = f"""📹 مدیریت ویدیو محصولات

📊 آمار:
✅ ویدیوهای آپلود شده: {uploaded_count}
📱 کل محصولات: {total_products}

💡 برای آپلود ویدیو محصول:
1. کد محصول را ارسال کنید
2. سپس ویدیو را ارسال کنید

لطفاً کد محصول مورد نظر را وارد کنید:
(مثال: CB001, PC001, DNS001)"""
        
        user_states[user_id] = {'waiting_for_product_video_code': True}
        keyboard = [[InlineKeyboardButton("📋 مشاهده لیست کدها", callback_data="view_product_codes")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "view_product_codes":
        if user_id not in ADMIN_IDS:
            return
        
        text = "📋 کدهای محصولات:\n\n"
        for product_key, product_info in PRODUCTS.items():
            video_status = "✅" if PRODUCT_VIDEOS.get(product_key) else "❌"
            text += f"{video_status} {product_info['code']}: {product_info['name']}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_product_videos")]]
        try:
            await query.edit_message_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text[:4096], reply_markup=InlineKeyboardMarkup(keyboard))

    # بخش تنظیمات پرداخت
    elif query.data == "admin_payment":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        card_number = payment_settings.get('card_number', '5859831176852845')
        card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
        
        text = f"""💳 تنظیمات پرداخت

🏦 شماره کارت فعلی: {card_number}
👤 نام صاحب کارت: {card_holder}

تنظیمات:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="change_card_number")],
            [InlineKeyboardButton("👤 تغییر نام صاحب کارت", callback_data="change_card_holder")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "change_card_number":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_card_number': True}
        text = """💳 تغییر شماره کارت

لطفاً شماره کارت جدید را وارد کنید:

⚠️ فقط اعداد وارد کنید (بدون فاصله یا خط تیره)"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_payment")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "change_card_holder":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_card_holder': True}
        text = """👤 تغییر نام صاحب کارت

لطفاً نام و نام خانوادگی صاحب کارت جدید را وارد کنید:"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_payment")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Handler های اندروید گم شده
    elif query.data == "android_config":
        keyboard = [
            [InlineKeyboardButton("🥉 کانفیگ بیسیک", callback_data="android_config_basic")],
            [InlineKeyboardButton("⭐ کانفیگ کاستوم", callback_data="android_config_custom")],
            [InlineKeyboardButton("💎 کانفیگ خصوصی", callback_data="android_config_private")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "⚙️ کانفیگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "⚙️ کانفیگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_dns":
        keyboard = [
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="android_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="android_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="android_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="android_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="android_dns_legendary")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🌐 DNS اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🌐 DNS اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_wireguard":
        keyboard = [
            [InlineKeyboardButton("1️⃣ تک لوکیشن", callback_data="android_wireguard_single")],
            [InlineKeyboardButton("2️⃣ دو لوکیشن", callback_data="android_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ سه لوکیشن", callback_data="android_wireguard_triple")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🔒 وایرگاد اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🔒 وایرگاد اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_host":
        keyboard = [
            [InlineKeyboardButton("🥉 هاست بیسیک", callback_data="android_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="android_host_vip")],
            [InlineKeyboardButton("⭐ هاست کاستوم", callback_data="android_host_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🏠 هاست اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🏠 هاست اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "android_fixlag":
        keyboard = [
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="android_fixlag_basic")],
            [InlineKeyboardButton("📈 افزایش FPS", callback_data="android_fixlag_fps")],
            [InlineKeyboardButton("⚡ FPS + کاهش لگ", callback_data="android_fixlag_fps_plus")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_android")]
        ]
        try:
            await query.edit_message_text(
                "🔧 فیکس لگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🔧 فیکس لگ اندروید:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # بقیه handlerهای موجود...
    # مدیریت کاربران اصلاح شده
    elif query.data == "admin_users":
        if query.from_user.id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        keyboard = [
            [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_block_user")],
            [InlineKeyboardButton("✅ رفع مسدودیت کاربر", callback_data="admin_unblock_user")],
            [InlineKeyboardButton("📋 لیست کاربران مسدود", callback_data="admin_blocked_list")],
            [InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user")],
            [InlineKeyboardButton("🗑️ حذف کاربر", callback_data="admin_delete_user")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            "👥 مدیریت کاربران:\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "admin_block_user":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_block_user_id': True}
        text = """🚫 مسدود کردن کاربر

لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:

💡 نکته: آیدی عددی کاربر در پیام‌های مدیریت نمایش داده می‌شود"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_users")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_unblock_user":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_unblock_user_id': True}
        text = """✅ رفع مسدودیت کاربر

لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_users")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_blocked_list":
        if user_id not in ADMIN_IDS:
            return
        
        if not user_blocked:
            text = "📋 هیچ کاربری مسدود نیست."
        else:
            text = f"📋 کاربران مسدود ({len(user_blocked)} نفر):\n\n"
            for blocked_user in list(user_blocked)[:10]:  # نمایش 10 نفر اول
                user_info = user_data.get(str(blocked_user), {})
                name = user_info.get('first_name', 'نامشخص')
                text += f"👤 {name} - آیدی: {blocked_user}\n"
            
            if len(user_blocked) > 10:
                text += f"\n... و {len(user_blocked) - 10} نفر دیگر"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_search_user":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_search_user': True}
        text = """🔍 جستجوی کاربر

لطفاً آیدی عددی، نام کاربری (بدون @) یا نام کاربر را وارد کنید:

مثال:
- 123456789 (آیدی عددی)
- username (نام کاربری)
- نام کاربر"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_users")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_delete_user":
        if user_id not in ADMIN_IDS:
            return
        
        user_states[user_id] = {'waiting_for_delete_user_id': True}
        text = """🗑️ حذف کاربر

⚠️ هشدار: این عمل غیرقابل بازگشت است!

لطفاً آیدی عددی کاربر مورد نظر را وارد کنید:

💡 پس از حذف، تمام اطلاعات کاربر (موجودی، سفارشات و...) پاک خواهد شد"""
        
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_users")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # باقی handlerها...
    # ادامه کد بقیه handlerها (حساب کاربری، خرید و...)
    elif query.data == "user_account":
        user_info = get_user_info(user_id)
        
        text = f"""👤 حساب کاربری

🆔 آیدی: {user_id}
👤 نام: {user_info['first_name']}
📱 نام کاربری: @{user_info['username'] if user_info['username'] else 'ندارد'}
💰 موجودی: {user_info['balance']:,} تومان
🛒 تعداد سفارشات: {user_info['orders_count']}
🎁 زیرمجموعه‌ها: {user_info.get('referrals', 0)} نفر
📅 تاریخ عضویت: {user_info['join_date'][:10]}
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 افزایش موجودی", callback_data="charge_account")],
            [InlineKeyboardButton("🎁 سیستم رفرال", callback_data="referral")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "charge_account":
        text = """💰 شارژ حساب - کارت به کارت

لطفاً مبلغ مورد نظر را به تومان وارد کنید:

💡 حداقل مبلغ شارژ: 5,000 تومان

📝 مثال: 10000 یا 50000 یا 100000"""
        
        user_states[user_id] = {'waiting_for_charge_amount': True}
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="user_account")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "charge_card_to_card":
        if user_id not in user_states or 'charge_amount' not in user_states[user_id]:
            try:
                await query.edit_message_text(
                    "❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید.",
                    reply_markup=main_menu(user_id)
                )
            except Exception:
                await query.message.reply_text(
                    "❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید.",
                    reply_markup=main_menu(user_id)
                )
            return
        
        amount = user_states[user_id]['charge_amount']
        card_number = payment_settings.get('card_number', '5859831176852845')
        card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
        
        text = f"""💳 شارژ حساب - کارت به کارت

🧾 فاکتور شارژ:
💰 مبلغ: {amount:,} تومان
🆔 آیدی: {user_id}

💳 اطلاعات کارت:
شماره کارت: {card_number}
نام صاحب کارت: {card_holder}

📋 مراحل پرداخت:
1️⃣ مبلغ {amount:,} تومان را به کارت بالا واریز کنید
2️⃣ عکس رسید را ارسال کنید

✅ رسید ارسال شده برای مدیران ارسال خواهد شد"""
        
        user_states[user_id] = {
            'waiting_for_charge_receipt': True,
            'charge_amount': amount,
            'payment_method': 'card_to_card'
        }
        
        keyboard = [[InlineKeyboardButton("🔙 لغو شارژ", callback_data="user_account")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Handler های پرداخت
    elif query.data.startswith("payment_"):
        product_key = query.data.replace("payment_", "")
        await process_payment(query, product_key)

    elif query.data.startswith("balance_"):
        product_key = query.data.replace("balance_", "")
        await process_balance_payment(query, product_key, context)

    elif query.data.startswith("discount_"):
        product_key = query.data.replace("discount_", "")
        await process_discount_code(query, product_key)

    # تایید/رد شارژ
    elif query.data.startswith("approve_charge_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_charge = int(query.data.replace("approve_charge_", ""))
        
        # پیدا کردن درخواست شارژ
        for uid, state in user_states.items():
            if int(uid) == user_to_charge and state.get('charge_pending_approval'):
                amount = state['charge_amount']
                update_user_balance(user_to_charge, amount)
                
                # حذف درخواست از حالت انتظار
                del user_states[uid]
                
                # اطلاع به کاربر
                try:
                    await context.bot.send_message(
                        user_to_charge,
                        f"✅ شارژ حساب شما تایید شد!\n\n💰 مبلغ {amount:,} تومان به حساب شما اضافه شد."
                    )
                except:
                    pass
                
                try:
                    await query.edit_message_text(
                        f"✅ شارژ حساب کاربر {user_to_charge} به مبلغ {amount:,} تومان تایید شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                except Exception:
                    await query.message.reply_text(
                        f"✅ شارژ حساب کاربر {user_to_charge} به مبلغ {amount:,} تومان تایید شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                break

    elif query.data.startswith("reject_charge_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_reject = int(query.data.replace("reject_charge_", ""))
        
        # پیدا کردن درخواست شارژ
        for uid, state in user_states.items():
            if int(uid) == user_to_reject and state.get('charge_pending_approval'):
                amount = state['charge_amount']
                
                # حذف درخواست از حالت انتظار
                del user_states[uid]
                
                # اطلاع به کاربر
                try:
                    await context.bot.send_message(
                        user_to_reject,
                        f"❌ درخواست شارژ حساب شما رد شد!\n\n💰 مبلغ: {amount:,} تومان\n\nلطفاً با پشتیبانی تماس بگیرید."
                    )
                except:
                    pass
                
                try:
                    await query.edit_message_text(
                        f"❌ درخواست شارژ حساب کاربر {user_to_reject} رد شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                except Exception:
                    await query.message.reply_text(
                        f"❌ درخواست شارژ حساب کاربر {user_to_reject} رد شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                break

    # تایید/رد آپدیت محصولات
    elif query.data.startswith("approve_update_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_update = int(query.data.replace("approve_update_", ""))
        
        # اطلاع به کاربر
        try:
            await context.bot.send_message(
                user_to_update,
                "✅ درخواست آپدیت شما تایید شد!\n\n🎉 آپدیت جدید بزودی برای شما ارسال خواهد شد.\n\nاز صبر شما متشکریم! 🙏"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال پیام تایید آپدیت به کاربر {user_to_update}: {e}")
        
        try:
            await query.edit_message_text(
                f"✅ درخواست آپدیت کاربر {user_to_update} تایید شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )
        except Exception:
            await query.message.reply_text(
                f"✅ درخواست آپدیت کاربر {user_to_update} تایید شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )

    elif query.data.startswith("reject_update_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_reject = int(query.data.replace("reject_update_", ""))
        
        # اطلاع به کاربر
        try:
            await context.bot.send_message(
                user_to_reject,
                "❌ درخواست آپدیت شما رد شد!\n\nلطفاً با پشتیبانی تماس بگیرید و دلیل رد را بررسی کنید."
            )
        except Exception as e:
            logger.error(f"خطا در ارسال پیام رد آپدیت به کاربر {user_to_reject}: {e}")
        
        try:
            await query.edit_message_text(
                f"❌ درخواست آپدیت کاربر {user_to_reject} رد شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )
        except Exception:
            await query.message.reply_text(
                f"❌ درخواست آپدیت کاربر {user_to_reject} رد شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )

    # تایید خرید محصول
    elif query.data.startswith("approve_purchase_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_approve = int(query.data.replace("approve_purchase_", ""))
        
        # پیدا کردن درخواست خرید
        for uid, state in user_states.items():
            if int(uid) == user_to_approve and state.get('waiting_for_receipt'):
                product_key = state['product_key']
                product_name = state['product_name']
                amount = state['amount']
                
                # آپدیت آمار کاربر
                increase_user_orders(user_to_approve)
                
                # آپدیت آمار محصولات
                if product_key in product_stats:
                    product_stats[product_key]['purchases'] += 1
                    product_stats[product_key]['revenue'] += amount
                    if state.get('discount_applied'):
                        product_stats[product_key]['discount_usage'] += 1
                
                # آپدیت آمار کلی
                user_stats['successful_purchases'] += 1
                user_stats['total_revenue'] += amount
                if state.get('discount_applied'):
                    user_stats['discount_codes_used'] += 1
                
                # حذف درخواست از حالت انتظار
                del user_states[uid]
                save_user_data()
                
                # ارسال محصول به کاربر
                await send_product_to_user(context.bot, user_to_approve, product_key, product_name)
                
                try:
                    await query.edit_message_text(
                        f"✅ خرید محصول {product_name} برای کاربر {user_to_approve} تایید شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                except Exception:
                    await query.message.reply_text(
                        f"✅ خرید محصول {product_name} برای کاربر {user_to_approve} تایید شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                break

    # رد خرید محصول
    elif query.data.startswith("reject_purchase_"):
        if query.from_user.id not in ADMIN_IDS:
            return
        
        user_to_reject = int(query.data.replace("reject_purchase_", ""))
        
        # پیدا کردن درخواست خرید
        for uid, state in user_states.items():
            if int(uid) == user_to_reject and state.get('waiting_for_receipt'):
                product_name = state['product_name']
                amount = state['amount']
                
                # حذف درخواست از حالت انتظار
                del user_states[uid]
                save_user_data()
                
                # اطلاع به کاربر
                try:
                    await context.bot.send_message(
                        user_to_reject,
                        f"❌ خرید محصول {product_name} رد شد!\n\n💰 مبلغ: {amount:,} تومان\n\nلطفاً با پشتیبانی تماس بگیرید و رسید معتبر ارسال کنید."
                    )
                except:
                    pass
                
                try:
                    await query.edit_message_text(
                        f"❌ خرید محصول {product_name} برای کاربر {user_to_reject} رد شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                except Exception:
                    await query.message.reply_text(
                        f"❌ خرید محصول {product_name} برای کاربر {user_to_reject} رد شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                    )
                break

    # آمار کلی ادمین
    elif query.data == "admin_stats":
        if query.from_user.id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        total_users = len(user_stats['total_users'])
        active_today = len(user_stats['active_users_today'])
        receipts = user_stats['receipts_submitted']
        successful = user_stats['successful_purchases']
        revenue = user_stats['total_revenue']
        discount_used = user_stats['discount_codes_used']
        
        text = f"""
📊 آمار کلی سیستم

👥 کل کاربران: {total_users:,} نفر
🟢 فعال امروز: {active_today:,} نفر
📮 رسیدهای ارسالی: {receipts:,} عدد
✅ خریدهای موفق: {successful:,} عدد
💰 کل درآمد: {revenue:,} تومان
🎫 کدهای تخفیف استفاده شده: {discount_used:,} عدد
        """
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # ارتباط با پشتیبانی
    elif query.data == "support":
        # شروع گفتگوی پشتیبانی
        user_states[user_id] = {
            'in_support_chat': True,
            'support_conversation_id': f"support_{user_id}_{int(datetime.now().timestamp())}"
        }
        
        text = """📞 بخش پشتیبانی

✅ شما وارد چت پشتیبانی شدید. 
💬 پیام خود را بنویسید تا به مدیران ارسال شود.

📱 همچنین می‌توانید مستقیماً در پیوی مالک پیام دهید: @Im_KIA_YT

⚡ مدیران می‌توانند مستقیماً به پیام‌های شما پاسخ دهند.

🔥 شما الان در حالت چت پشتیبانی هستید - هر پیامی بفرستید برای مدیران ارسال می‌شود."""
        
        keyboard = [
            [InlineKeyboardButton("❌ خروج از چت پشتیبانی", callback_data="exit_support")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # خروج از چت پشتیبانی
    elif query.data == "exit_support":
        if user_id in user_states and user_states[user_id].get('in_support_chat'):
            del user_states[user_id]
        
        await query.edit_message_text(
            "✅ از چت پشتیبانی خارج شدید",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )

    # سیستم رفرال
    elif query.data == "referral":
        bot_username = context.bot.username
        referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        text = f"""🎁 سیستم رفرال

🔗 لینک رفرال شما:
{referral_link}

💰 هر کاربر با لینک شما به ربات بیاد مبلغ 2000 تومان به حساب شما واریز می‌شود

⚠️ توجه: هر کاربر فقط یک بار می‌تواند از لینک رفرال استفاده کند"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Handler های مدیریت admin
    elif query.data.startswith("reply_to_"):
        user_target_id = int(query.data.replace("reply_to_", ""))
        user_states[user_id] = {'waiting_for_admin_reply': True, 'target_user': user_target_id}
        text = "💬 لطفاً پیام خود را برای ارسال به کاربر تایپ کنید:\n\n📎 می‌توانید فایل هم ارسال کنید"
        keyboard = [[InlineKeyboardButton("🔙 لغو", callback_data="admin_panel")]]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("block_"):
        if user_id not in ADMIN_IDS:
            return
        
        user_target_id = int(query.data.replace("block_", ""))
        user_blocked.add(user_target_id)
        save_user_data()
        await query.answer("🚫 کاربر مسدود شد", show_alert=True)

    elif query.data.startswith("unblock_"):
        if user_id not in ADMIN_IDS:
            return
        
        user_target_id = int(query.data.replace("unblock_", ""))
        if user_target_id in user_blocked:
            user_blocked.remove(user_target_id)
            save_user_data()
            await query.answer("🔓 کاربر رفع مسدودی شد", show_alert=True)
        else:
            await query.answer("❌ کاربر مسدود نیست", show_alert=True)

    elif query.data.startswith("warn_"):
        if user_id not in ADMIN_IDS:
            return
        
        user_target_id = int(query.data.replace("warn_", ""))
        try:
            await context.bot.send_message(user_target_id, "⚠️ اخطار: لطفاً قوانین ربات را رعایت کنید")
            await query.answer("⚠️ اخطار ارسال شد", show_alert=True)
        except Exception:
            await query.answer("❌ خطا در ارسال اخطار", show_alert=True)

    # بقیه handlerها برای محصولات و خرید...
    # سایت
    elif query.data == "site":
        keyboard = [
            [InlineKeyboardButton("⭐ نسخه ویژه", callback_data="site_premium")],
            [InlineKeyboardButton("📦 نسخه عادی", callback_data="site_normal")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "🌐 سایت - انتخاب نسخه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "site_premium":
        text = f"""
⭐ نسخه ویژه سایت

با خرید اشتراک پک ویژه به مدت 50 روز و هدیه پک عادی فقط با قیمت 800T

✅4 نوع کانفیگ به ارزش 3 میلیون + کانفیگ خصوصی به دستور خودتون ساخته میشه 

✅ پیش از چند ده تا سرور های گیمینگ وایرگارد + DNS گیمینگ به ارزش 5 میلیون

✅ هاست گیمینگ همراه با اپ اختصاصی به ارزش 2 میلیون تومان

💰 قیمت: {PRODUCTS['site_premium']['price']:,} تومان
📱 کد محصول: {PRODUCTS['site_premium']['code']}
        """
        
        # ارسال ویدیو اگر موجود باشد
        if SITE_VIDEO_FILE_ID:
            try:
                try:
                    await query.edit_message_text("🔄 در حال آماده‌سازی...")
                except Exception:
                    await query.message.reply_text("🔄 در حال آماده‌سازی...")
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=SITE_VIDEO_FILE_ID,
                    caption=text,
                    reply_markup=create_purchase_buttons("site_premium", "site", query.from_user.id)
                )
                await context.bot.delete_message(query.message.chat_id, query.message.message_id)
            except Exception as e:
                logger.error(f"خطا در ارسال ویدیو سایت: {e}")
                await query.edit_message_text(text, reply_markup=create_purchase_buttons("site_premium", "site", query.from_user.id))
        else:
            await query.edit_message_text(text, reply_markup=create_purchase_buttons("site_premium", "site", query.from_user.id))

    elif query.data == "site_normal":
        text = f"""
📦 نسخه عادی سایت

با خرید اشتراک پک عادی به مدت 40 روز فقط با قیمت :400

2 نوع کانفیگ به ارزش 1 میلیون

پیش از چند ده تا سرور های گیمینگ وایرگارد به ارزش 3 میلیون 

هاست گیمینگ همراه با اپ اختصاصی به ارزش 1 میلیون

💰 قیمت: {PRODUCTS['site_normal']['price']:,} تومان
📱 کد محصول: {PRODUCTS['site_normal']['code']}
        """
        
        # ارسال ویدیو اگر موجود باشد
        if SITE_VIDEO_FILE_ID:
            try:
                try:
                    await query.edit_message_text("🔄 در حال آماده‌سازی...")
                except Exception:
                    await query.message.reply_text("🔄 در حال آماده‌سازی...")
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=SITE_VIDEO_FILE_ID,
                    caption=text,
                    reply_markup=create_purchase_buttons("site_normal", "site", query.from_user.id)
                )
                await context.bot.delete_message(query.message.chat_id, query.message.message_id)
            except Exception as e:
                logger.error(f"خطا در ارسال ویدیو سایت: {e}")
                await query.edit_message_text(text, reply_markup=create_purchase_buttons("site_normal", "site", query.from_user.id))
        else:
            await query.edit_message_text(text, reply_markup=create_purchase_buttons("site_normal", "site", query.from_user.id))

    # بقیه handlerها برای iOS و PC و updates
    elif query.data == "buy_ios":
        keyboard = [
            [InlineKeyboardButton("🎮 چیت", callback_data="ios_cheat")],
            [InlineKeyboardButton("🌐 DNS", callback_data="ios_dns")],
            [InlineKeyboardButton("🔒 وایرگاد", callback_data="ios_wireguard")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")]
        ]
        try:
            await query.edit_message_text(
                "🍎 محصولات آیفون:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🍎 محصولات آیفون:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "buy_pc":
        user_states[user_id] = {'platform_context': 'pc'}
        keyboard = [
            [InlineKeyboardButton("⚙️ کانفیگ", callback_data="pc_config")],
            [InlineKeyboardButton("🌐 DNS", callback_data="pc_dns")],
            [InlineKeyboardButton("🔒 وایرگاد", callback_data="pc_wireguard")],
            [InlineKeyboardButton("🏠 هاست", callback_data="pc_host")],
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="pc_fixlag")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy")]
        ]
        try:
            await query.edit_message_text(
                "💻 محصولات پیسی:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "💻 محصولات پیسی:\n\nلطفاً محصول مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # iOS محصولات
    elif query.data == "ios_cheat":
        cheat_text = editable_texts.get('ios_cheat', 'درحال اپدیت')
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="buy_ios")]]
        try:
            await query.edit_message_text(
                f"🎮 چیت آیفون:\n\n{cheat_text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                f"🎮 چیت آیفون:\n\n{cheat_text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "show_ios_cheat_product":
        product = PRODUCTS["ios_cheat"]
        text = f"""🎮 چیت آیفون

📱 نام محصول: {product['name']}
💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}

✨ ویژگی‌ها:
{editable_texts.get('ios_cheat', 'درحال اپدیت')}"""
        
        try:
            await query.edit_message_text(
                text, 
                reply_markup=create_purchase_buttons("ios_cheat", "buy_ios", user_id)
            )
        except Exception:
            await query.message.reply_text(
                text, 
                reply_markup=create_purchase_buttons("ios_cheat", "buy_ios", user_id)
            )

    elif query.data == "ios_dns":
        user_states[user_id] = {'platform_context': 'ios'}
        keyboard = [
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="ios_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="ios_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="ios_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="ios_dns_exclusive")],
            [InlineKeyboardButton("🏆 DNS لجندری", callback_data="ios_dns_legendary")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_ios")]
        ]
        try:
            await query.edit_message_text(
                "🌐 DNS آیفون:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🌐 DNS آیفون:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "ios_wireguard":
        user_states[user_id] = {'platform_context': 'ios'}
        keyboard = [
            [InlineKeyboardButton("1️⃣ تک لوکیشن", callback_data="ios_wireguard_single")],
            [InlineKeyboardButton("2️⃣ دو لوکیشن", callback_data="ios_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ سه لوکیشن", callback_data="ios_wireguard_triple")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_ios")]
        ]
        try:
            await query.edit_message_text(
                "🔒 وایرگاد آیفون:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            await query.message.reply_text(
                "🔒 وایرگاد آیفون:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # PC محصولات
    elif query.data == "pc_config":
        keyboard = [
            [InlineKeyboardButton("🥉 BASIC بیسیک", callback_data="pc_config_basic")],
            [InlineKeyboardButton("👑 VVIP وی وی آی پی", callback_data="pc_config_vvip")],
            [InlineKeyboardButton("⭐ custom کاستوم", callback_data="pc_config_custom")],
            [InlineKeyboardButton("💎 private خصوصی", callback_data="pc_config_private")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_pc")]
        ]
        await query.edit_message_text(
            "⚙️ کانفیگ پیسی:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "pc_dns":
        keyboard = [
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="pc_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="pc_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="pc_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="pc_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="pc_dns_legendary")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_pc")]
        ]
        await query.edit_message_text(
            "🌐 DNS پیسی:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "pc_wireguard":
        keyboard = [
            [InlineKeyboardButton("1️⃣ تک لوکیشن", callback_data="pc_wireguard_single")],
            [InlineKeyboardButton("2️⃣ دو لوکیشن", callback_data="pc_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ سه لوکیشن", callback_data="pc_wireguard_triple")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_pc")]
        ]
        await query.edit_message_text(
            "🔒 وایرگاد پیسی:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "pc_host":
        keyboard = [
            [InlineKeyboardButton("🥉 هاست بیسیک", callback_data="pc_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="pc_host_vip")],
            [InlineKeyboardButton("⭐ هاست کاستوم", callback_data="pc_host_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_pc")]
        ]
        await query.edit_message_text(
            "🏠 هاست پیسی:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "pc_fixlag":
        keyboard = [
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="pc_fixlag_basic")],
            [InlineKeyboardButton("📈 افزایش FPS", callback_data="pc_fixlag_fps")],
            [InlineKeyboardButton("⚡ FPS + کاهش لگ", callback_data="pc_fixlag_fps_plus")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_pc")]
        ]
        await query.edit_message_text(
            "🔧 فیکس لگ پیسی:\n\nلطفاً پکیج مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # محصولات خاص - PC Config
    elif query.data == "pc_config_basic":
        text = f"""
⚙️ کانفیگ BASIC بیسیک پیسی

💰 قیمت: {PRODUCTS['pc_config_basic']['price']:,} تومان
📱 کد محصول: {PRODUCTS['pc_config_basic']['code']}
"""
        await query.edit_message_text(text, reply_markup=create_purchase_buttons("pc_config_basic", "pc_config", query.from_user.id))

    elif query.data == "pc_config_vvip":
        text = f"""
👑 کانفیگ VVIP وی وی آی پی پیسی

💰 قیمت: {PRODUCTS['pc_config_vvip']['price']:,} تومان
📱 کد محصول: {PRODUCTS['pc_config_vvip']['code']}
"""
        await query.edit_message_text(text, reply_markup=create_purchase_buttons("pc_config_vvip", "pc_config", query.from_user.id))

    elif query.data == "pc_config_custom":
        text = f"""
⭐ کانفیگ custom کاستوم پیسی

💰 قیمت: {PRODUCTS['pc_config_custom']['price']:,} تومان
📱 کد محصول: {PRODUCTS['pc_config_custom']['code']}
"""
        await query.edit_message_text(text, reply_markup=create_purchase_buttons("pc_config_custom", "pc_config", query.from_user.id))

    elif query.data == "pc_config_private":
        text = f"""
💎 کانفیگ private خصوصی پیسی

💰 قیمت: {PRODUCTS['pc_config_private']['price']:,} تومان
📱 کد محصول: {PRODUCTS['pc_config_private']['code']}
"""
        await query.edit_message_text(text, reply_markup=create_purchase_buttons("pc_config_private", "pc_config", query.from_user.id))

    # DNS Products Handlers
    elif query.data.startswith(("android_dns_", "ios_dns_", "pc_dns_")):
        dns_type = query.data.split("_")[-1]  # bronze, platinum, elite, exclusive, legendary
        platform = query.data.split("_")[0]  # android, ios, pc
        
        dns_products = {
            "bronze": "dns_bronze",
            "platinum": "dns_platinum", 
            "elite": "dns_elite",
            "exclusive": "dns_exclusive",
            "legendary": "dns_legendary"
        }
        
        if dns_type in dns_products:
            product_key = dns_products[dns_type]
            product = PRODUCTS[product_key]
            text = f"""🌐 {product['name']} {platform.upper()}

✨ ویژگی‌ها:
• سرعت بالا و پایداری عالی
• مناسب گیمینگ و استفاده روزانه
• پشتیبانی کامل

💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}"""
            try:
                await query.edit_message_text(text, reply_markup=create_purchase_buttons(product_key, f"{platform}_dns", query.from_user.id))
            except Exception:
                await query.message.reply_text(text, reply_markup=create_purchase_buttons(product_key, f"{platform}_dns", query.from_user.id))

    # WireGuard Products Handlers
    elif query.data.startswith(("android_wireguard_", "ios_wireguard_", "pc_wireguard_")):
        wg_type = query.data.split("_")[-1]  # single, dual, triple
        platform = query.data.split("_")[0]  # android, ios, pc
        
        wg_products = {
            "single": "wireguard_single",
            "dual": "wireguard_dual",
            "triple": "wireguard_triple"
        }
        
        if wg_type in wg_products:
            product_key = wg_products[wg_type]
            product = PRODUCTS[product_key]
            
            # تعیین توضیحات بر اساس نوع
            if wg_type == "single":
                features = "• یک لوکیشن اختصاصی\n• سرعت عالی\n• امنیت بالا"
            elif wg_type == "dual":
                features = "• دو لوکیشن مختلف\n• انتخاب سرور\n• پایداری بیشتر"
            else:  # triple
                features = "• سه لوکیشن متنوع\n• گزینه‌های بیشتر\n• حداکثر انعطاف‌پذیری"
            
            text = f"""🔒 {product['name']} {platform.upper()}

✨ ویژگی‌ها:
{features}

💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}"""
            try:
                await query.edit_message_text(text, reply_markup=create_purchase_buttons(product_key, f"{platform}_wireguard", query.from_user.id))
            except Exception:
                await query.message.reply_text(text, reply_markup=create_purchase_buttons(product_key, f"{platform}_wireguard", query.from_user.id))

    # Host Products Handlers (PC only)
    elif query.data.startswith("pc_host_"):
        host_type = query.data.split("_")[-1]  # basic, vip, custom
        
        host_products = {
            "basic": "host_basic",
            "vip": "host_vip", 
            "custom": "host_custom"
        }
        
        if host_type in host_products:
            product_key = host_products[host_type]
            product = PRODUCTS[product_key]
            text = f"""
🏠 {product['name']}

💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}
"""
            await query.edit_message_text(text, reply_markup=create_purchase_buttons(product_key, "pc_host", query.from_user.id))

    # FixLag Products Handlers
    elif query.data.startswith(("android_fixlag_", "pc_fixlag_")):
        fixlag_type = query.data.split("_")[-1]  # basic, fps, fps_plus
        platform = query.data.split("_")[0]  # android, pc
        
        if fixlag_type == "fps":
            fixlag_type = "fps"
        elif fixlag_type == "plus":
            fixlag_type = "fps_plus"
        
        fixlag_products = {
            "basic": "fixlag_basic",
            "fps": "fixlag_fps",
            "fps_plus": "fixlag_fps_plus"
        }
        
        if fixlag_type in fixlag_products:
            product_key = fixlag_products[fixlag_type]
            product = PRODUCTS[product_key]
            duration = product.get('duration', '')
            text = f"""
🔧 {product['name']}

⏱️ مدت زمان: {duration}
💰 قیمت: {product['price']:,} تومان
📱 کد محصول: {product['code']}
"""
            await query.edit_message_text(text, reply_markup=create_purchase_buttons(product_key, f"{platform}_fixlag", query.from_user.id))

    # آپدیت محصولات
    elif query.data == "updates":
        keyboard = [
            [InlineKeyboardButton("📱 اندروید", callback_data="update_android")],
            [InlineKeyboardButton("🍎 آیفون", callback_data="update_ios")],
            [InlineKeyboardButton("💻 پیسی", callback_data="update_pc")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "📱 آپدیت محصولات:\n\nلطفاً پلتفرم مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "update_android":
        keyboard = [
            [InlineKeyboardButton("⚙️ کانفیگ بیسیک", callback_data="update_android_config_basic")],
            [InlineKeyboardButton("⭐ کانفیگ کاستوم", callback_data="update_android_config_custom")],
            [InlineKeyboardButton("💎 کانفیگ خصوصی", callback_data="update_android_config_private")],
            [InlineKeyboardButton("🎮 چیت اندروید", callback_data="update_android_cheat")],
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="update_android_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="update_android_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="update_android_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="update_android_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="update_android_dns_legendary")],
            [InlineKeyboardButton("1️⃣ وایرگاد تک لوکیشن", callback_data="update_android_wireguard_single")],
            [InlineKeyboardButton("2️⃣ وایرگاد دو لوکیشن", callback_data="update_android_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ وایرگاد سه لوکیشن", callback_data="update_android_wireguard_triple")],
            [InlineKeyboardButton("🥉 هاست بیسیک", callback_data="update_android_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="update_android_host_vip")],
            [InlineKeyboardButton("⭐ هاست کاستوم", callback_data="update_android_host_custom")],
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="update_android_fixlag_basic")],
            [InlineKeyboardButton("📈 افزایش FPS", callback_data="update_android_fixlag_fps")],
            [InlineKeyboardButton("⚡ FPS + کاهش لگ", callback_data="update_android_fixlag_fps_plus")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="updates")]
        ]
        await query.edit_message_text(
            "📱 آپدیت محصولات اندروید:\n\nلطفاً محصول مورد نظر را برای آپدیت انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "update_ios":
        keyboard = [
            [InlineKeyboardButton("🎮 چیت آیفون", callback_data="update_ios_cheat")],
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="update_ios_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="update_ios_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="update_ios_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="update_ios_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="update_ios_dns_legendary")],
            [InlineKeyboardButton("1️⃣ وایرگاد تک لوکیشن", callback_data="update_ios_wireguard_single")],
            [InlineKeyboardButton("2️⃣ وایرگاد دو لوکیشن", callback_data="update_ios_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ وایرگاد سه لوکیشن", callback_data="update_ios_wireguard_triple")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="updates")]
        ]
        await query.edit_message_text(
            "🍎 آپدیت محصولات آیفون:\n\nلطفاً محصول مورد نظر را برای آپدیت انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "update_pc":
        keyboard = [
            [InlineKeyboardButton("🥉 کانفیگ BASIC بیسیک", callback_data="update_pc_config_basic")],
            [InlineKeyboardButton("👑 کانفیگ VVIP وی وی آی پی", callback_data="update_pc_config_vvip")],
            [InlineKeyboardButton("⭐ کانفیگ custom کاستوم", callback_data="update_pc_config_custom")],
            [InlineKeyboardButton("💎 کانفیگ private خصوصی", callback_data="update_pc_config_private")],
            [InlineKeyboardButton("🥉 DNS برنز", callback_data="update_pc_dns_bronze")],
            [InlineKeyboardButton("🥈 DNS پلاتینیوم", callback_data="update_pc_dns_platinum")],
            [InlineKeyboardButton("🥇 DNS آلیت", callback_data="update_pc_dns_elite")],
            [InlineKeyboardButton("💎 DNS اکسکلوسیو", callback_data="update_pc_dns_exclusive")],
            [InlineKeyboardButton("👑 DNS لجندری", callback_data="update_pc_dns_legendary")],
            [InlineKeyboardButton("1️⃣ وایرگاد تک لوکیشن", callback_data="update_pc_wireguard_single")],
            [InlineKeyboardButton("2️⃣ وایرگاد دو لوکیشن", callback_data="update_pc_wireguard_dual")],
            [InlineKeyboardButton("3️⃣ وایرگاد سه لوکیشن", callback_data="update_pc_wireguard_triple")],
            [InlineKeyboardButton("🥉 هاست بیسیک", callback_data="update_pc_host_basic")],
            [InlineKeyboardButton("👑 هاست VIP", callback_data="update_pc_host_vip")],
            [InlineKeyboardButton("⭐ هاست کاستوم", callback_data="update_pc_host_custom")],
            [InlineKeyboardButton("🔧 فیکس لگ", callback_data="update_pc_fixlag_basic")],
            [InlineKeyboardButton("📈 افزایش FPS", callback_data="update_pc_fixlag_fps")],
            [InlineKeyboardButton("⚡ FPS + کاهش لگ", callback_data="update_pc_fixlag_fps_plus")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="updates")]
        ]
        await query.edit_message_text(
            "💻 آپدیت محصولات پیسی:\n\nلطفاً محصول مورد نظر را برای آپدیت انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Handlers یکپارچه برای همه محصولات آپدیت - تمام محصولات پیام یکسان دارند
    elif query.data.startswith("update_") and query.data not in ["update_android", "update_ios", "update_pc"]:
        # تشخیص پلتفرم و کتگوری برای بازگشت درست
        platform = ""
        category = ""
        if "android" in query.data:
            back_callback = "update_android"
            platform = "Android"
        elif "ios" in query.data:
            back_callback = "update_ios"
            platform = "iOS"
        elif "pc" in query.data:
            back_callback = "update_pc"
            platform = "PC"
        else:
            back_callback = "updates"
            platform = "General"
            
        # تعیین کتگوری و نام محصول بر اساس callback data
        product_name = ""
        
        if "config" in query.data:
            category = "Config"
            if "basic" in query.data:
                product_name = "کانفیگ بیسیک"
            elif "custom" in query.data:
                product_name = "کانفیگ کاستوم"
            elif "private" in query.data:
                product_name = "کانفیگ خصوصی"
            else:
                product_name = "کانفیگ"
        elif "dns" in query.data:
            category = "DNS"
            if "bronze" in query.data:
                product_name = "DNS برنز"
            elif "platinum" in query.data:
                product_name = "DNS پلاتینیوم"
            elif "elite" in query.data:
                product_name = "DNS آلیت"
            elif "exclusive" in query.data:
                product_name = "DNS اکسکلوسیو"
            elif "legendary" in query.data:
                product_name = "DNS لجندری"
            else:
                product_name = "DNS"
        elif "wireguard" in query.data:
            category = "WireGuard"
            if "single" in query.data:
                product_name = "وایرگاد تک لوکیشن"
            elif "dual" in query.data:
                product_name = "وایرگاد دو لوکیشن"
            elif "triple" in query.data:
                product_name = "وایرگاد سه لوکیشن"
            else:
                product_name = "وایرگاد"
        elif "host" in query.data:
            category = "Host"
            if "basic" in query.data:
                product_name = "هاست اختصاصی بیسیک"
            elif "vip" in query.data:
                product_name = "هاست اختصاصی VIP"
            elif "custom" in query.data:
                product_name = "هاست اختصاصی کاستوم"
            else:
                product_name = "هاست"
        elif "fixlag" in query.data:
            category = "FixLag"
            if "basic" in query.data:
                product_name = "فیکس لگ"
            elif "fps" in query.data and "plus" not in query.data:
                product_name = "کانفیگ افزایش FPS"
            elif "fps" in query.data and "plus" in query.data:
                product_name = "کانفیگ FPS + کاهش لگ"
            else:
                product_name = "فیکس لگ"
        elif "cheat" in query.data:
            category = "Cheat"
            if "android" in query.data:
                product_name = "چیت اندروید"
            elif "ios" in query.data:
                product_name = "چیت آیفون"
            else:
                product_name = "چیت"
        else:
            category = "Product"
            product_name = "محصول"
            
        # تنظیم state برای آپدیت
        user_states[user_id] = {
            'waiting_for_update_receipt': True,
            'update_category': f'{platform} {category}',
            'platform': platform,
            'product_name': product_name,
            'callback_data': query.data
        }
            
        text = "🔄 لطفاً رسید و کد محصول را ارسال کنید."
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # سیستم تمدید جدید - درخواست کلمه تمدید
    elif query.data.startswith("update_extension_"):
        original_callback = query.data.replace("update_extension_", "")
        
        # دریافت اطلاعات محصول از state قبلی کاربر
        if user_id in user_states and 'product_name' in user_states[user_id]:
            product_name = user_states[user_id]['product_name']
            platform = user_states[user_id]['platform']
        else:
            # اگر state موجود نبود، تعیین نام محصول از callback
            platform = ""
            product_name = ""
            if "android" in original_callback:
                platform = "Android"
            elif "ios" in original_callback:
                platform = "iOS"
            elif "pc" in original_callback:
                platform = "PC"
                
            if "config" in original_callback:
                product_name = "کانفیگ"
            elif "dns" in original_callback:
                product_name = "DNS"
            elif "wireguard" in original_callback:
                product_name = "وایرگاد"
            elif "host" in original_callback:
                product_name = "هاست"
            elif "fixlag" in original_callback:
                product_name = "فیکس لگ"
            elif "cheat" in original_callback:
                product_name = "چیت"
            else:
                product_name = "محصول"
        
        # تنظیم state برای انتظار کلمه تمدید
        user_states[user_id] = {
            'waiting_for_extension_keyword': True,
            'product_name': product_name,
            'platform': platform,
            'original_callback': original_callback
        }
        
        text = f"🔄 تمدید {product_name} {platform}\n\nلطفاً کلمه 'تمدید' را وارد کنید:"
        
        # تعیین callback برای بازگشت
        back_callback = "updates"
        if "android" in original_callback:
            back_callback = "update_android"
        elif "ios" in original_callback:
            back_callback = "update_ios"  
        elif "pc" in original_callback:
            back_callback = "update_pc"
            
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)]
        ]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # پرداخت کارت به کارت برای تمدید
    elif query.data.startswith("extension_payment_"):
        extension_code = query.data.replace("extension_payment_", "")
        if extension_code in extension_codes:
            ext_info = extension_codes[extension_code]
            
            if not ext_info.get('valid', False):
                await query.answer("❌ کد تمدید منقضی شده است!", show_alert=True)
                return
                
            product_key = ext_info.get('product', '')
            if product_key in PRODUCTS:
                product = PRODUCTS[product_key]
                extension_price = ext_info.get('price', product['price'] // 2)
                
                # ذخیره اطلاعات پرداخت تمدید
                user_states[user_id] = {
                    'waiting_for_extension_receipt': True,
                    'extension_code': extension_code,
                    'product_key': product_key,
                    'product_name': product['name'],
                    'extension_price': extension_price
                }
                
                card_number = payment_settings.get('card_number', '5859831176852845')
                card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
                
                payment_text = f"""💳 پرداخت تمدید

🔄 تمدید محصول: {product['name']}
💰 مبلغ قابل پرداخت: {extension_price:,} تومان
🎫 کد تمدید: {extension_code}

☑️ لطفا مبلغ {extension_price:,} تومان به کارت زیر واریز کنید

💳 شماره کارت:
{card_number}
بنام {card_holder}

لطفاً رسید و عکس کسر موجودی با کد تمدید رو بفرستید ✅
🎫 کد تمدید: {extension_code}"""
                
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
                
                try:
                    await query.edit_message_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))
                except Exception:
                    await query.message.reply_text(payment_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("❌ کد تمدید یافت نشد!", show_alert=True)

    # کسر از موجودی برای تمدید
    elif query.data.startswith("extension_balance_"):
        extension_code = query.data.replace("extension_balance_", "")
        if extension_code in extension_codes:
            ext_info = extension_codes[extension_code]
            
            if not ext_info.get('valid', False):
                await query.answer("❌ کد تمدید منقضی شده است!", show_alert=True)
                return
                
            product_key = ext_info.get('product', '')
            if product_key in PRODUCTS:
                product = PRODUCTS[product_key]
                extension_price = ext_info.get('price', product['price'] // 2)
                user_info = get_user_info(user_id)
                
                # بررسی موجودی کافی
                if user_info['balance'] < extension_price:
                    text = f"""❌ موجودی ناکافی!

💰 موجودی فعلی: {user_info['balance']:,} تومان
💳 قیمت تمدید: {extension_price:,} تومان
📉 کمبود: {extension_price - user_info['balance']:,} تومان

لطفاً ابتدا حساب خود را شارژ کنید."""
                    
                    keyboard = [
                        [InlineKeyboardButton("💰 شارژ حساب", callback_data="charge_account")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                    ]
                    try:
                        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    except Exception:
                        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
                    return
                
                # کسر مبلغ از موجودی
                user_info['balance'] -= extension_price
                user_info['extensions'] = user_info.get('extensions', 0) + 1
                save_user_data()
                
                # غیرفعال کردن کد تمدید
                extension_codes[extension_code]['valid'] = False
                save_user_data()
                
                # ارسال اطلاعات تمدید برای مدیران
                extension_text = f"""🔄 درخواست تمدید جدید (کسر از موجودی)

👤 کاربر: {query.from_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
👤 نام کاربری: @{query.from_user.username or 'ندارد'}

🔄 محصول: {product['name']}
💰 مبلغ: {extension_price:,} تومان
🎫 کد تمدید: {extension_code}

💳 روش پرداخت: کسر از موجودی
✅ مبلغ از موجودی کسر شد"""
                
                # دکمه‌های مدیریت برای مدیران
                admin_keyboard = [
                    [InlineKeyboardButton("✅ تایید تمدید", callback_data=f"approve_extension_{user_id}_{extension_code}")],
                    [InlineKeyboardButton("❌ رد تمدید", callback_data=f"reject_extension_{user_id}_{extension_code}")],
                    [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")]
                ]
                
                # ارسال برای همه مدیران
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            admin_id, 
                            extension_text, 
                            reply_markup=InlineKeyboardMarkup(admin_keyboard)
                        )
                    except Exception as e:
                        logger.error(f"خطا در ارسال پیام به مدیر {admin_id}: {e}")
                
                # پیام تایید برای کاربر
                success_text = f"""✅ درخواست تمدید ثبت شد!

🔄 محصول: {product['name']}
💰 مبلغ پرداختی: {extension_price:,} تومان
🎫 کد تمدید: {extension_code}

💰 موجودی باقیمانده: {user_info['balance']:,} تومان

درخواست تمدید شما در اسرع وقت بررسی و تایید خواهد شد."""
                
                keyboard = [[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]]
                try:
                    await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))
                except Exception:
                    await query.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("❌ کد تمدید یافت نشد!", show_alert=True)

    # زیرمنوهای پنل مدیریت تمدید
    elif query.data == "admin_create_extension_code":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        # انتخاب محصول برای ساخت کد تمدید
        keyboard = []
        for product_key, product in PRODUCTS.items():
            keyboard.append([InlineKeyboardButton(f"📦 {product['name']}", callback_data=f"create_ext_code_{product_key}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_extension")])
        
        text = """🎫 ساخت کد تمدید

لطفاً محصولی که می‌خواهید برای آن کد تمدید بسازید را انتخاب کنید:"""
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("create_ext_code_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
            
        product_key = query.data.replace("create_ext_code_", "")
        if product_key in PRODUCTS:
            product = PRODUCTS[product_key]
            default_price = product['price'] // 2  # قیمت پیش‌فرض نصف قیمت اصلی
            
            user_states[user_id] = {
                'creating_extension_code': True,
                'extension_product': product_key,
                'extension_product_name': product['name'],
                'extension_price': default_price,
                'step': 'extension_code'
            }
            
            text = f"""🎫 ساخت کد تمدید برای {product['name']}

💰 قیمت پیش‌فرض تمدید: {default_price:,} تومان

1️⃣ لطفاً کد تمدید مورد نظر را وارد کنید:
(مثال: EXT123456)"""
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_create_extension_code")]]
            
            try:
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "admin_extension_requests":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        # نمایش درخواست‌های تمدید
        pending_requests = []
        for uid, udata in user_data.items():
            if udata.get('extensions', 0) > 0:
                pending_requests.append((uid, udata))
        
        if not pending_requests:
            text = "📋 درخواست‌های تمدید\n\n❌ هیچ درخواست تمدیدی یافت نشد."
        else:
            text = f"📋 درخواست‌های تمدید\n\n📊 تعداد کل: {len(pending_requests)}\n\n"
            for uid, udata in pending_requests[:10]:  # نمایش 10 درخواست اول
                name = udata.get('first_name', 'نامشخص')
                extensions = udata.get('extensions', 0)
                text += f"👤 {name} | 🆔 {uid} | 🔄 {extensions} تمدید\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_extension")]]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


    elif query.data == "admin_extension_stats":
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        # محاسبه آمار تمدید
        total_extensions = sum(udata.get('extensions', 0) for udata in user_data.values())
        users_with_extension = sum(1 for udata in user_data.values() if udata.get('extensions', 0) > 0)
        active_codes = sum(1 for code_info in extension_codes.values() if code_info.get('valid', False))
        used_codes = sum(1 for code_info in extension_codes.values() if not code_info.get('valid', False))
        
        text = f"""📊 آمار تمدید

📈 آمار کلی:
👥 کل کاربران: {len(user_data)}
🔄 کاربران با تمدید: {users_with_extension}
📊 کل تمدیدها: {total_extensions}

🎫 آمار کدها:
✅ کدهای فعال: {active_codes}
❌ کدهای استفاده شده: {used_codes}
📋 کل کدها: {len(extension_codes)}

💰 درآمد تخمینی از تمدید: محاسبه نشده"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_extension")]]
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # تایید تمدید توسط مدیر
    elif query.data.startswith("approve_extension_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        try:
            parts = query.data.replace("approve_extension_", "").split("_")
            target_user_id = int(parts[0])
            extension_code = parts[1] if len(parts) > 1 else ""
            
            # ارسال پیام تایید به کاربر
            success_message = f"""✅ تمدید شما تایید شد!

🎫 کد تمدید: {extension_code}
🔄 محصول شما با موفقیت تمدید شد.

از انتخاب ما متشکریم! 🙏"""
            
            try:
                await context.bot.send_message(target_user_id, success_message)
                
                # پیام تایید برای مدیر
                await query.edit_message_text(
                    f"✅ تمدید کاربر {target_user_id} تایید شد!\n\nپیام تایید برای کاربر ارسال گردید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin_panel")]])
                )
                
                logger.info(f"تمدید کاربر {target_user_id} توسط مدیر {user_id} تایید شد")
                
            except Exception as e:
                await query.edit_message_text(
                    f"❌ خطا در ارسال پیام به کاربر {target_user_id}: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin_panel")]])
                )
                
        except (ValueError, IndexError):
            await query.answer("❌ فرمت اطلاعات نامعتبر است!", show_alert=True)

    # رد تمدید توسط مدیر
    elif query.data.startswith("reject_extension_"):
        if user_id not in ADMIN_IDS:
            await query.answer("⛔ شما مجاز به استفاده از این بخش نیستید!")
            return
        
        try:
            parts = query.data.replace("reject_extension_", "").split("_")
            target_user_id = int(parts[0])
            extension_code = parts[1] if len(parts) > 1 else ""
            
            # بازگردانی کد تمدید به حالت فعال (اگر کسر از موجودی بوده)
            if extension_code in extension_codes:
                extension_codes[extension_code]['valid'] = True
                save_user_data()
            
            # ارسال پیام رد به کاربر
            reject_message = f"""❌ درخواست تمدید شما رد شد

🎫 کد تمدید: {extension_code}
📝 دلیل: نیازمند بررسی بیشتر

💬 برای اطلاعات بیشتر با پشتیبانی تماس بگیرید:
@KIA_YT021_VIP_BOT0"""
            
            try:
                await context.bot.send_message(target_user_id, reject_message)
                
                # پیام تایید برای مدیر
                await query.edit_message_text(
                    f"❌ تمدید کاربر {target_user_id} رد شد!\n\nپیام رد برای کاربر ارسال گردید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin_panel")]])
                )
                
                logger.info(f"تمدید کاربر {target_user_id} توسط مدیر {user_id} رد شد")
                
            except Exception as e:
                await query.edit_message_text(
                    f"❌ خطا در ارسال پیام به کاربر {target_user_id}: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin_panel")]])
                )
                
        except (ValueError, IndexError):
            await query.answer("❌ فرمت اطلاعات نامعتبر است!", show_alert=True)

    # ادامه چت پشتیبانی
    elif query.data == "continue_support":
        user_states[user_id] = {
            'in_support_chat': True,
            'support_conversation_id': f"support_{user_id}_{int(datetime.now().timestamp())}"
        }
        
        await query.edit_message_text(
            "💬 چت پشتیبانی ادامه یافت.\n\nپیام خود را بنویسید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ خروج از چت", callback_data="exit_support")]])
        )
    
    # پاسخ سریع مدیر
    elif query.data.startswith("quick_reply_"):
        target_user_id = int(query.data.replace("quick_reply_", ""))
        
        user_states[user_id] = {
            'waiting_for_quick_reply': True,
            'target_user_id': target_user_id
        }
        
        await query.edit_message_text(
            f"💬 پاسخ سریع به کاربر {target_user_id}\n\nپیام خود را بنویسید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="admin_panel")]])
        )
    
    # بستن چت پشتیبانی توسط مدیر
    elif query.data.startswith("close_support_"):
        target_user_id = int(query.data.replace("close_support_", ""))
        
        # اطلاع به کاربر
        try:
            await context.bot.send_message(
                target_user_id,
                "❌ چت پشتیبانی توسط مدیر بسته شد.\n\nبرای شروع چت جدید از منو استفاده کنید."
            )
        except:
            pass
        
        # حذف state کاربر
        if target_user_id in user_states:
            del user_states[target_user_id]
        
        await query.edit_message_text(
            f"✅ چت پشتیبانی کاربر {target_user_id} بسته شد."
        )

    # Handler اضافی برای main_menu
    elif query.data == "main_menu":
        await query.edit_message_text(
            "🏠 منوی اصلی:\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=main_menu(query.from_user.id)
        )

# ارسال محصول به کاربر
async def send_product_to_user(bot, user_id, product_key, product_name):
    """ارسال محصول به کاربر پس از تایید خرید"""
    try:
        # بررسی وجود ویدیو برای محصول
        if product_key in PRODUCT_VIDEOS and PRODUCT_VIDEOS[product_key]:
            # ارسال ویدیو محصول
            await bot.send_video(
                user_id,
                PRODUCT_VIDEOS[product_key],
                caption=f"✅ خرید شما تایید شد!\n\n🎁 محصول: {product_name}\n\nاز خرید شما متشکریم! 🙏"
            )
        else:
            # اگر ویدیو موجود نیست، پیام متنی ارسال کن
            success_message = f"""
✅ خرید شما تایید شد!

🎁 محصول: {product_name}

📱 لطفاً برای دریافت فایل محصول با پشتیبانی تماس بگیرید:
@KIA_YT021_VIP_BOT0

از خرید شما متشکریم! 🙏
"""
            await bot.send_message(user_id, success_message)
        
        logger.info(f"محصول {product_name} برای کاربر {user_id} ارسال شد")
    except Exception as e:
        logger.error(f"خطا در ارسال محصول به کاربر {user_id}: {e}")
        # ارسال پیام جایگزین در صورت خطا
        try:
            await bot.send_message(
                user_id,
                f"✅ خرید شما تایید شد!\n\n🎁 محصول: {product_name}\n\nبرای دریافت محصول با پشتیبانی تماس بگیرید."
            )
        except:
            pass

# پردازش ریپلای مدیران به پیام‌های پشتیبانی
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پاسخ مدیر به پیام پشتیبانی"""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    # فقط برای مدیران
    if user_id not in ADMIN_IDS:
        return
    
    # بررسی آیا این پیام ریپلای است
    if not update.message.reply_to_message:
        return
    
    # پیدا کردن کاربری که پیام اصلی مربوط به اوست
    replied_message_text = update.message.reply_to_message.text or ""
    
    # استخراج آیدی کاربر از متن پیام
    import re
    user_id_match = re.search(r"🆔 آیدی: (\d+)", replied_message_text)
    if not user_id_match:
        return
    
    target_user_id = int(user_id_match.group(1))
    admin_reply = update.message.text
    admin_name = update.effective_user.first_name or "پشتیبانی"
    
    # ارسال پاسخ مدیر به کاربر
    try:
        reply_text = f"""💬 پاسخ از پشتیبانی:

👤 {admin_name}: 
{admin_reply}

📅 {datetime.now().strftime('%H:%M')}"""
        
        await context.bot.send_message(
            target_user_id,
            reply_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 پاسخ دادن", callback_data="continue_support")]])
        )
        
        # تایید برای مدیر
        await update.message.reply_text(
            f"✅ پاسخ شما به کاربر {target_user_id} ارسال شد!"
        )
        
        logger.info(f"پاسخ پشتیبانی از مدیر {user_id} به کاربر {target_user_id} ارسال شد")
        
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ پشتیبانی: {e}")
        await update.message.reply_text(
            f"❌ خطا در ارسال پاسخ به کاربر {target_user_id}"
        )

# مدیریت پیام‌های متنی
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text if update.message.text else ""
    
    # بررسی آنتی اسپم
    if not check_anti_spam(user_id):
        await update.message.reply_text("⚠️ شما خیلی سریع پیام می‌فرستید. لطفاً کمی صبر کنید.")
        return
    
    # بررسی وجود state برای کاربر
    user_state = user_states.get(user_id, {})
    
    # پردازش پیام‌های چت پشتیبانی
    if user_state.get('in_support_chat'):
        logger.info(f"پیام پشتیبانی از کاربر {user_id}: {message_text[:50]}...")
        conversation_id = user_state.get('support_conversation_id', f"support_{user_id}")
        
        # ارسال پیام کاربر برای مدیران
        support_message = f"""💬 پیام جدید از پشتیبانی

👤 کاربر: {update.effective_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
👤 نام کاربری: @{update.effective_user.username or 'ندارد'}
📅 زمان: {datetime.now().strftime('%Y/%m/%d %H:%M')}

💬 پیام:
{message_text}

برای پاسخ، روی این پیام ریپلای کنید."""
        
        # دکمه‌های مدیریت برای مدیران
        admin_keyboard = [
            [InlineKeyboardButton("✅ تایید", callback_data=f"approve_support_{user_id}")],
            [InlineKeyboardButton("❌ رد", callback_data=f"reject_support_{user_id}")],
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")],
            [InlineKeyboardButton("🚫 مسدود", callback_data=f"block_{user_id}"), 
             InlineKeyboardButton("🔓 رفع مسدودی", callback_data=f"unblock_{user_id}")],
            [InlineKeyboardButton("⚠️ اخطار", callback_data=f"warn_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        support_message_sent = False
        sent_count = 0
        for admin_id in ADMIN_IDS:
            try:
                sent_message = await context.bot.send_message(
                    admin_id,
                    support_message,
                    reply_markup=InlineKeyboardMarkup(admin_keyboard)
                )
                
                # ذخیره آیدی پیام برای ریپلای
                if not support_message_sent:
                    user_states[user_id]['last_support_message_id'] = sent_message.message_id
                    user_states[user_id]['admin_chat_id'] = admin_id
                    support_message_sent = True
                
                sent_count += 1
                logger.info(f"پیام پشتیبانی با موفقیت به ادمین {admin_id} ارسال شد")
                    
            except Exception as e:
                logger.error(f"خطا در ارسال پیام پشتیبانی به مدیر {admin_id}: {e}")
        
        logger.info(f"پیام پشتیبانی به {sent_count}/{len(ADMIN_IDS)} مدیر ارسال شد")
        
        # پیام تایید برای کاربر (state را نگه می‌داریم)
        await update.message.reply_text(
            "✅ پیام شما به پشتیبانی ارسال شد.\n\nمنتظر پاسخ باشید...\n\nمی‌توانید پیام بعدی خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ خروج از چت", callback_data="exit_support")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ])
        )
        # state را نگه می‌داریم تا کاربر بتواند پیام‌های بیشتری ارسال کند
        return
    
    # پردازش کلمه تمدید در سیستم جدید
    if user_state.get('waiting_for_extension_keyword'):
        if message_text.strip().lower() in ['تمدید', 'tamdid']:
            # نمایش فاکتور تمدید
            product_name = user_state.get('product_name', 'محصول')
            platform = user_state.get('platform', '')
            
            # تخمین قیمت تمدید (نصف قیمت اصلی)
            estimated_price = 77000  # قیمت پیش‌فرض
            
            # تولید کد تمدید منحصر به فرد
            import random
            extension_code = f"EXT{user_id}_{random.randint(1000, 9999)}"
            
            # ذخیره کد تمدید
            extension_codes[extension_code] = {
                'user_id': user_id,
                'product_name': product_name,
                'price': estimated_price,
                'valid': True,
                'platform': platform,
                'created_at': datetime.now().isoformat()
            }
            save_user_data()
            
            card_number = payment_settings.get('card_number', '5859831176852845')
            card_holder = payment_settings.get('card_holder', 'کیارش ارامیده')
            
            invoice_text = f"""🧾 فاکتور تمدید
            
🔄 محصول: {product_name} {platform}
💰 مبلغ تمدید: {estimated_price:,} تومان
🎫 کد تمدید: {extension_code}

💳 کارت به کارت

☑️ لطفا مبلغ {estimated_price:,} تومان به کارت زیر واریز کنید

💳 شماره کارت:
{card_number}
بنام {card_holder}

لطفاً رسید و عکس کسر موجودی با کد تمدید رو بفرستید ✅
🎫 کد تمدید: {extension_code}"""
            
            # تنظیم state برای انتظار رسید تمدید
            user_states[user_id] = {
                'waiting_for_extension_receipt': True,
                'extension_code': extension_code,
                'product_name': product_name,
                'platform': platform,
                'extension_price': estimated_price
            }
            
            await update.message.reply_text(
                invoice_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
            
        else:
            await update.message.reply_text(
                "❌ کلمه صحیح نیست. لطفاً کلمه 'تمدید' را وارد کنید:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
        return
    
    # مدیریت ویرایش متن‌ها توسط ادمین
    if user_state.get('waiting_for_rules_text') and user_id in ADMIN_IDS:
        editable_texts['rules_text'] = message_text
        save_user_data()
        
        await update.message.reply_text(
            "✅ قوانین با موفقیت به‌روزرسانی شد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_rules")]])
        )
        del user_states[user_id]
        return
    
    if user_state.get('waiting_for_text_edit') and user_id in ADMIN_IDS:
        text_key = user_state['text_key']
        editable_texts[text_key] = message_text
        save_user_data()
        
        text_names = {
            'tutorial_android': 'آموزش Android',
            'tutorial_ios': 'آموزش iOS', 
            'tutorial_pc': 'آموزش PC',
            'android_cheat': 'چیت Android'
        }
        text_name = text_names.get(text_key, text_key)
        
        await update.message.reply_text(
            f"✅ {text_name} با موفقیت به‌روزرسانی شد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_texts")]])
        )
        del user_states[user_id]
        return
    
    # مدیریت تنظیمات پرداخت
    if user_state.get('waiting_for_card_number') and user_id in ADMIN_IDS:
        # بررسی صحت شماره کارت (16 رقم)
        if message_text.isdigit() and len(message_text) == 16:
            payment_settings['card_number'] = message_text
            save_user_data()
            
            await update.message.reply_text(
                "✅ شماره کارت با موفقیت به‌روزرسانی شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_payment")]])
            )
            del user_states[user_id]
        else:
            await update.message.reply_text(
                "❌ شماره کارت نامعتبر است! لطفاً 16 رقم وارد کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_payment")]])
            )
        return
    
    if user_state.get('waiting_for_card_holder') and user_id in ADMIN_IDS:
        payment_settings['card_holder'] = message_text.strip()
        save_user_data()
        
        await update.message.reply_text(
            "✅ نام صاحب کارت با موفقیت به‌روزرسانی شد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_payment")]])
        )
        del user_states[user_id]
        return
    
    # مدیریت پیام همگانی
    if user_state.get('waiting_for_broadcast_message') and user_id in ADMIN_IDS:
        await update.message.reply_text("⏳ در حال ارسال پیام همگانی...")
        
        # ارسال پیام همگانی
        success_count, failed_count = await broadcast_message(context.bot, message_text, user_id)
        
        result_text = f"""📊 نتیجه ارسال پیام همگانی:

✅ ارسال موفق: {success_count} کاربر
❌ ارسال ناموفق: {failed_count} کاربر

📝 پیام ارسال شده:
{message_text[:100]}{'...' if len(message_text) > 100 else ''}"""
        
        await update.message.reply_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
        )
        del user_states[user_id]
        return
    
    # مدیریت کانال‌های اضافی
    if user_state.get('waiting_for_new_channel') and user_id in ADMIN_IDS:
        channel_input = message_text.strip()
        
        # پردازش و اعتبارسنجی ورودی کانال
        if channel_input.startswith('https://t.me/'):
            # استخراج نام کانال از لینک
            channel_name = '@' + channel_input.split('/')[-1]
        elif channel_input.startswith('@'):
            channel_name = channel_input
        elif channel_input.startswith('t.me/'):
            channel_name = '@' + channel_input.split('/')[-1]
        else:
            # اگر فقط نام کانال باشد، @ اضافه کن
            channel_name = '@' + channel_input if not channel_input.startswith('@') else channel_input
        
        # بررسی اینکه کانال قبلاً اضافه نشده باشد
        if channel_name in ADDITIONAL_CHANNELS:
            await update.message.reply_text(
                f"❌ کانال {channel_name} قبلاً در لیست موجود است!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]])
            )
        else:
            # تست عضویت در کانال برای اطمینان از صحت
            try:
                # تست با آیدی خود ادمین
                await context.bot.get_chat_member(channel_name, user_id)
                
                # اضافه کردن کانال به لیست
                ADDITIONAL_CHANNELS.append(channel_name)
                save_user_data()
                
                await update.message.reply_text(
                    f"✅ کانال {channel_name} با موفقیت اضافه شد!\n\n📋 تعداد کانال‌های اضافی: {len(ADDITIONAL_CHANNELS)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]])
                )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ خطا در اضافه کردن کانال {channel_name}!\n\n💡 لطفاً مطمئن شوید که:\n• کانال عمومی است\n• نام کانال صحیح است\n• ربات به کانال دسترسی دارد\n\nخطا: {str(e)[:100]}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]])
                )
        
        del user_states[user_id]
        return
    
    if user_state.get('waiting_for_channel_to_remove') and user_id in ADMIN_IDS:
        try:
            channel_number = int(message_text.strip())
            
            if channel_number < 1 or channel_number > len(ADDITIONAL_CHANNELS):
                await update.message.reply_text(
                    f"❌ شماره کانال نامعتبر است! لطفاً عددی بین 1 تا {len(ADDITIONAL_CHANNELS)} وارد کنید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="view_channels")]])
                )
            else:
                # حذف کانال
                removed_channel = ADDITIONAL_CHANNELS.pop(channel_number - 1)
                save_user_data()
                
                await update.message.reply_text(
                    f"✅ کانال {removed_channel} با موفقیت حذف شد!\n\n📋 تعداد کانال‌های باقیمانده: {len(ADDITIONAL_CHANNELS)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_membership")]])
                )
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً شماره کانال را به صورت عدد وارد کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="view_channels")]])
            )
        
        del user_states[user_id]
        return

    # مدیریت کاربران
    if user_state.get('waiting_for_block_user_id') and user_id in ADMIN_IDS:
        try:
            target_user_id = int(message_text.strip())
            user_blocked.add(target_user_id)
            save_user_data()
            
            await update.message.reply_text(
                f"✅ کاربر {target_user_id} مسدود شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
            del user_states[user_id]
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً آیدی عددی معتبر وارد کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
        return
    
    if user_state.get('waiting_for_unblock_user_id') and user_id in ADMIN_IDS:
        try:
            target_user_id = int(message_text.strip())
            if target_user_id in user_blocked:
                user_blocked.remove(target_user_id)
                save_user_data()
                status_text = f"✅ کاربر {target_user_id} از حالت مسدود خارج شد!"
            else:
                status_text = f"⚠️ کاربر {target_user_id} قبلاً مسدود نبوده است."
            
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
            del user_states[user_id]
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً آیدی عددی معتبر وارد کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
        return
    
    if user_state.get('waiting_for_search_user') and user_id in ADMIN_IDS:
        search_term = message_text.strip()
        found_users = []
        
        # جستجو در user_data
        for uid, info in user_data.items():
            if (search_term in str(uid) or 
                search_term.lower() in info.get('first_name', '').lower() or 
                search_term.lower() in info.get('username', '').lower()):
                
                found_users.append({
                    'id': uid,
                    'name': info.get('first_name', 'نامشخص'),
                    'username': info.get('username', 'ندارد'),
                    'balance': info.get('balance', 0),
                    'orders': info.get('orders_count', 0)
                })
        
        if found_users:
            text = f"🔍 نتایج جستجو برای '{search_term}':\n\n"
            for user in found_users[:5]:  # نمایش 5 نتیجه اول
                status = "🚫 مسدود" if int(user['id']) in user_blocked else "✅ فعال"
                text += f"👤 {user['name']}\n"
                text += f"🆔 آیدی: {user['id']}\n"
                text += f"📱 یوزر: @{user['username']}\n"
                text += f"💰 موجودی: {user['balance']:,} تومان\n"
                text += f"🛒 سفارشات: {user['orders']}\n"
                text += f"📊 وضعیت: {status}\n\n"
        else:
            text = f"❌ هیچ کاربری با عبارت '{search_term}' یافت نشد."
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
        )
        del user_states[user_id]
        return
    
    if user_state.get('waiting_for_delete_user_id') and user_id in ADMIN_IDS:
        try:
            target_user_id = message_text.strip()
            if target_user_id in user_data:
                user_name = user_data[target_user_id].get('first_name', 'نامشخص')
                del user_data[target_user_id]
                # حذف از مسدودها هم اگر باشد
                user_blocked.discard(int(target_user_id))
                save_user_data()
                
                status_text = f"✅ کاربر {user_name} (آیدی: {target_user_id}) با موفقیت حذف شد!"
            else:
                status_text = f"❌ کاربری با آیدی {target_user_id} یافت نشد."
            
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
            del user_states[user_id]
        except Exception as e:
            await update.message.reply_text(
                "❌ خطا در حذف کاربر! لطفاً آیدی صحیح وارد کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]])
            )
        return
    
    # مدیریت پاسخ سریع ادمین
    if user_state.get('waiting_for_quick_reply') and user_id in ADMIN_IDS:
        target_user_id = user_state.get('target_user_id')
        if not target_user_id:
            await update.message.reply_text("❌ خطا در شناسایی کاربر مقصد!")
            del user_states[user_id]
            return
        
        try:
            admin_name = update.effective_user.first_name or "پشتیبانی"
            
            reply_text = f"""💬 پاسخ از پشتیبانی:

👤 {admin_name}:
{message_text}

📅 {datetime.now().strftime('%H:%M')}"""
            
            await context.bot.send_message(
                target_user_id,
                reply_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 پاسخ دادن", callback_data="continue_support")]])
            )
            
            await update.message.reply_text(
                f"✅ پاسخ سریع شما به کاربر {target_user_id} ارسال شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )
            
        except Exception as e:
            logger.error(f"خطا در ارسال پاسخ سریع: {e}")
            await update.message.reply_text(
                f"❌ خطا در ارسال پاسخ به کاربر {target_user_id}"
            )
        
        del user_states[user_id]
        return
    
    # مدیریت پاسخ ادمین به کاربر
    if user_state.get('waiting_for_admin_reply') and user_id in ADMIN_IDS:
        target_user_id = user_state.get('target_user')
        if not target_user_id:
            await update.message.reply_text("❌ خطا در شناسایی کاربر مقصد!")
            del user_states[user_id]
            return
        
        try:
            # ارسال پیام متنی
            if update.message.text:
                await context.bot.send_message(
                    target_user_id,
                    f"💬 پیام از پشتیبانی:\n\n{update.message.text}"
                )
            
            # ارسال عکس
            elif update.message.photo:
                caption = f"💬 پیام از پشتیبانی"
                if update.message.caption:
                    caption += f":\n\n{update.message.caption}"
                    
                await context.bot.send_photo(
                    target_user_id,
                    update.message.photo[-1].file_id,
                    caption=caption
                )
            
            # ارسال ویدیو
            elif update.message.video:
                caption = f"💬 پیام از پشتیبانی"
                if update.message.caption:
                    caption += f":\n\n{update.message.caption}"
                    
                await context.bot.send_video(
                    target_user_id,
                    update.message.video.file_id,
                    caption=caption
                )
            
            # ارسال فایل/سند
            elif update.message.document:
                caption = f"💬 پیام از پشتیبانی"
                if update.message.caption:
                    caption += f":\n\n{update.message.caption}"
                    
                await context.bot.send_document(
                    target_user_id,
                    update.message.document.file_id,
                    caption=caption
                )
            
            # ارسال صدا
            elif update.message.voice:
                await context.bot.send_voice(
                    target_user_id,
                    update.message.voice.file_id
                )
                await context.bot.send_message(
                    target_user_id,
                    "💬 پیام صوتی از پشتیبانی"
                )
            
            # ارسال استیکر
            elif update.message.sticker:
                await context.bot.send_sticker(
                    target_user_id,
                    update.message.sticker.file_id
                )
                await context.bot.send_message(
                    target_user_id,
                    "💬 پیام از پشتیبانی"
                )
            
            # پیام تایید برای ادمین
            await update.message.reply_text(
                "✅ پیام شما با موفقیت به کاربر ارسال شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )
            
        except Exception as e:
            logger.error(f"خطا در ارسال پیام ادمین به کاربر {target_user_id}: {e}")
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام!\n\nممکن است کاربر ربات را بلاک کرده باشد یا آیدی اشتباه باشد.\n\nخطا: {str(e)[:100]}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
            )
        
        del user_states[user_id]
        return
    
    # پردازش رسید آپدیت محصولات
    if user_state.get('waiting_for_update_receipt'):
        # ارسال رسید آپدیت برای مدیران
        user_data_info = get_user_info(user_id)
        update_receipt_text = f"""🔄 درخواست آپدیت محصول

👤 کاربر: {update.effective_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{update.effective_user.username or 'ندارد'}
📱 پلتفرم: {user_state.get('platform', 'General')}
📋 کتگوری: {user_state.get('update_category', 'Product Update')}

📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}

📝 متن پیام:
{message_text or 'فقط عکس ارسال شده'}"""
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید آپدیت", callback_data=f"approve_update_{user_id}")],
            [InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject_update_{user_id}")],
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        sent_count = 0
        for admin_id in ADMIN_IDS:
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        admin_id,
                        update.message.photo[-1].file_id,
                        caption=update_receipt_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await context.bot.send_message(
                        admin_id,
                        update_receipt_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                sent_count += 1
                logger.info(f"رسید آپدیت با موفقیت برای ادمین {admin_id} ارسال شد")
            except Exception as e:
                logger.error(f"خطا در ارسال رسید آپدیت به ادمین {admin_id}: {e}")
        
        logger.info(f"رسید آپدیت برای {sent_count}/{len(ADMIN_IDS)} ادمین ارسال شد")
        
        # پیام تایید برای کاربر
        await update.message.reply_text(
            "✅ درخواست آپدیت شما دریافت شد!\n\nلطفاً منتظر بررسی و ارسال آپدیت باشید.",
            reply_markup=main_menu(user_id)
        )
        
        # حذف state کاربر
        del user_states[user_id]
        return

    # پردازش رسید تمدید (عکس + متن) - فقط در صورت ریپلای
    if user_state.get('waiting_for_extension_receipt'):
        # بررسی که پیام ریپلای شده باشد
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کارت به کارت ریپلای کنید!\n\n💡 راهنما:\n1. روی پیام کارت به کارت کلیک کنید\n2. گزینه Reply را انتخاب کنید\n3. عکس رسید را ارسال کنید",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
            return
        # ارسال پیام تایید به کاربر
        extension_code = user_state.get('extension_code', '')
        product_name = user_state.get('product_name', '')
        extension_price = user_state.get('extension_price', 0)
        
        await update.message.reply_text(
            f"✅ رسید تمدید شما دریافت شد!\n\n🔄 محصول: {product_name}\n💰 مبلغ: {extension_price:,} تومان\n🎫 کد تمدید: {extension_code}\n\nدرخواست تمدید شما در اسرع وقت بررسی خواهد شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        
        # ارسال اطلاعات تمدید برای مدیران
        if update.message.photo:
            file_type = "🖼️ عکس"
        elif update.message.document:
            file_type = "📄 فایل"
        else:
            file_type = "📝 متن"
            
        extension_text = f"""🔄 درخواست تمدید جدید (کارت به کارت)

👤 کاربر: {update.effective_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
👤 نام کاربری: @{update.effective_user.username or 'ندارد'}

🔄 محصول: {product_name}
💰 مبلغ: {extension_price:,} تومان
🎫 کد تمدید: {extension_code}
📎 نوع رسید: {file_type}

💳 روش پرداخت: کارت به کارت"""
        
        # دکمه‌های مدیریت برای مدیران
        admin_keyboard = [
            [InlineKeyboardButton("✅ تایید تمدید", callback_data=f"approve_extension_{user_id}_{extension_code}")],
            [InlineKeyboardButton("❌ رد تمدید", callback_data=f"reject_extension_{user_id}_{extension_code}")],
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        for admin_id in ADMIN_IDS:
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        admin_id,
                        update.message.photo[-1].file_id,
                        caption=extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        admin_id,
                        update.message.document.file_id,
                        caption=extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
                else:
                    await context.bot.send_message(
                        admin_id,
                        extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به مدیر {admin_id}: {e}")
        
        # غیرفعال کردن کد تمدید
        if extension_code in extension_codes:
            extension_codes[extension_code]['valid'] = False
            save_user_data()
        
        del user_states[user_id]
        return

    # پردازش رسیدها (عکس + متن) - فقط در صورت ریپلای
    if user_state.get('waiting_for_receipt'):
        # بررسی که پیام ریپلای شده باشد
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کارت به کارت ریپلای کنید!\n\n💡 راهنما:\n1. روی پیام کارت به کارت کلیک کنید\n2. گزینه Reply را انتخاب کنید\n3. عکس رسید را ارسال کنید",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
            return
        
        # ارسال رسید برای مدیران
        user_data_info = get_user_info(user_id)
        receipt_text = f"""
💳 رسید جدید دریافت شد!

👤 کاربر: {update.effective_user.first_name}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{update.effective_user.username if update.effective_user.username else 'ندارد'}
🛍️ محصول: {user_state['product_name']}
💰 مبلغ: {user_state['amount']:,} تومان
📋 کد محصول: {user_state['product_code']}

{f"🎫 کد تخفیف: {user_state['discount_code']} ({user_state.get('discount_amount', 0):,} تومان تخفیف)" if user_state.get('discount_applied') else ""}

📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}
"""
        
        keyboard = [
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")],
            [InlineKeyboardButton("🚫 مسدود کردن", callback_data=f"block_{user_id}")],
            [InlineKeyboardButton("🔓 حذف مسدود", callback_data=f"unblock_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        for admin_id in ADMIN_IDS:
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        admin_id,
                        update.message.photo[-1].file_id,
                        caption=receipt_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await context.bot.send_message(
                        admin_id,
                        receipt_text + f"\n📝 متن: {message_text}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال رسید به ادمین {admin_id}: {e}")
        
        # پیام تایید برای کاربر
        await update.message.reply_text(
            "✅ رسید شما دریافت شد!\n\nلطفاً منتظر تایید پرداخت باشید. بزودی نتیجه به اطلاع شما خواهد رسید.",
            reply_markup=main_menu(user_id)
        )
        
        # آپدیت آمار
        user_stats['receipts_submitted'] += 1
        save_user_data()
        
        # حذف state کاربر
        del user_states[user_id]
        return

    # پردازش مبلغ شارژ
    if user_state.get('waiting_for_charge_amount'):
        try:
            # پاک کردن کاراکترهای اضافه و تبدیل به عدد
            amount_str = message_text.strip().replace(',', '').replace(' ', '').replace('تومان', '').replace('T', '').replace('t', '')
            amount = int(amount_str)
            
            if amount < 5000:
                await update.message.reply_text(
                    "❌ مبلغ شارژ باید بیشتر از 5,000 تومان باشد!\n\nلطفاً مبلغ مورد نظر را دوباره وارد کنید:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="user_account")]])
                )
                return
            
            # ذخیره مبلغ در state برای نمایش در فاکتور
            user_states[user_id] = {
                'charge_amount': amount,
                'waiting_for_charge_method': True
            }
            
            # نمایش فاکتور با روش‌های پرداخت
            text = f"""🧾 فاکتور شارژ حساب

💰 مبلغ شارژ: {amount:,} تومان
🆔 آیدی شما: {user_id}

لطفاً روش پرداخت را انتخاب کنید:"""
            
            keyboard = [
                [InlineKeyboardButton("💳 کارت به کارت", callback_data="charge_card_to_card")],
                [InlineKeyboardButton("🔙 لغو شارژ", callback_data="user_account")]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            
        except ValueError:
            await update.message.reply_text(
                "❌ مبلغ وارد شده نامعتبر است!\n\nلطفاً فقط عدد وارد کنید (مثال: 10000)\n\n💡 مثال‌هایی که می‌توانید وارد کنید:\n• 10000\n• 50000\n• 100000",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="user_account")]])
            )
        except Exception as e:
            logger.error(f"خطا در پردازش مبلغ شارژ برای کاربر {user_id}: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش مبلغ!\n\nلطفاً دوباره تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="user_account")]])
            )
        return

    # پردازش رسید شارژ - فقط در صورت ریپلای
    if user_state.get('waiting_for_charge_receipt'):
        # بررسی که پیام ریپلای شده باشد
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ لطفاً روی پیام کارت به کارت ریپلای کنید!\n\n💡 راهنما:\n1. روی پیام کارت به کارت کلیک کنید\n2. گزینه Reply را انتخاب کنید\n3. عکس رسید را ارسال کنید",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
            return
        # بررسی ارسال فایل - رد کردن فایل
        if update.message.document:
            await update.message.reply_text(
                "❌ لطفاً عکس یا متن ارسال کنید!\n\nفایل قابل قبول نیست.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
            )
            return
            
        # بررسی که حداقل عکس یا متن ارسال شده باشد
        has_photo = bool(update.message.photo)
        has_text = bool(message_text and message_text.strip())
        
        if not has_photo and not has_text:
            await update.message.reply_text(
                "❌ لطفاً عکس رسید یا متن حاوی اطلاعات پرداخت را ارسال کنید",
                reply_markup=main_menu(user_id)
            )
            return
            
        # تعیین نوع رسید
        try:
            if has_photo:
                file_id = update.message.photo[-1].file_id
                file_type = "🖼️ عکس رسید"
                logger.info(f"عکس رسید شارژ دریافت شد - User: {user_id}, Photo ID: {file_id}")
            else:
                file_id = None
                file_type = "📝 متن رسید"
                logger.info(f"متن رسید شارژ دریافت شد - User: {user_id}, Text: {message_text[:50]}...")
        except (IndexError, AttributeError) as e:
            logger.error(f"خطا در دریافت file_id: {e}")
            await update.message.reply_text(
                "❌ خطا در پردازش. لطفاً دوباره ارسال کنید.",
                reply_markup=main_menu(user_id)
            )
            return
            
        # ارسال رسید شارژ برای مدیران - با اطلاعات کامل
        user_data_info = get_user_info(user_id)
        charge_receipt_text = f"""💰 درخواست شارژ حساب جدید

👤 کاربر: {update.effective_user.first_name or 'نامشخص'}
🆔 آیدی کاربر: {user_id}
📱 یوزرنیم: @{update.effective_user.username or 'ندارد'}
💳 مبلغ درخواستی: {user_state['charge_amount']:,} تومان
💰 موجودی فعلی: {user_data_info.get('balance', 0):,} تومان

📎 نوع رسید: {file_type}
📅 تاریخ: {datetime.now().strftime('%Y/%m/%d %H:%M')}

⚠️ لطفاً رسید و مدارک را بررسی کنید."""
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید شارژ", callback_data=f"approve_charge_{user_id}")],
            [InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject_charge_{user_id}")],
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        sent_count = 0
        total_admins = len(ADMIN_IDS)
        
        for admin_id in ADMIN_IDS:
            try:
                if has_photo:
                    # ارسال عکس رسید با اطلاعات کامل
                    logger.info(f"⏳ در حال ارسال عکس رسید شارژ به مدیر {admin_id}")
                    
                    # تنظیم caption برای عکس
                    photo_caption = charge_receipt_text
                    if has_text:
                        photo_caption += f"\n\n📝 متن همراه عکس: {message_text}"
                    
                    sent_message = await context.bot.send_photo(
                        admin_id,
                        update.message.photo[-1].file_id,
                        caption=photo_caption,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    logger.info(f"✅ عکس رسید شارژ با موفقیت برای مدیر {admin_id} ارسال شد - Message ID: {sent_message.message_id}")
                    
                else:
                    # ارسال پیام متنی فقط
                    text_with_message = charge_receipt_text
                    if has_text:
                        text_with_message += f"\n\n📝 متن رسید: {message_text}"
                    else:
                        text_with_message += f"\n\n⚠️ هیچ متن اضافی ارسال نشده است"
                    
                    sent_message = await context.bot.send_message(
                        admin_id,
                        text_with_message,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    logger.info(f"✅ متن رسید شارژ با موفقیت برای مدیر {admin_id} ارسال شد")
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"❌ خطا در ارسال رسید به مدیر {admin_id}: {e}")
                
                # تلاش مجدد با پیام متنی ساده
                try:
                    fallback_text = charge_receipt_text
                    if message_text:
                        fallback_text += f"\n\n📝 متن: {message_text}"
                    fallback_text += f"\n\n❌ خطا در ارسال {file_type} - لطفاً از کاربر رسید جدید بخواهید"
                    
                    await context.bot.send_message(
                        admin_id,
                        fallback_text,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    sent_count += 1
                    logger.info(f"✅ پیام جایگزین رسید شارژ برای مدیر {admin_id} ارسال شد")
                except Exception as e2:
                    logger.error(f"❌ خطای کامل در ارسال به مدیر {admin_id}: {e2}")
        
        logger.info(f"📊 خلاصه ارسال رسید شارژ: {sent_count}/{total_admins} مدیر دریافت کردند")
        
        # اگر هیچ مدیری پیام را دریافت نکرد
        if sent_count == 0:
            logger.error("⚠️ هیچ مدیری رسید شارژ را دریافت نکرد!")
            await update.message.reply_text(
                "⚠️ مشکلی در ارسال رسید برای مدیران رخ داده است.\n\nلطفاً مستقیماً با پشتیبانی تماس بگیرید:\n@Im_KIA_YT",
                reply_markup=main_menu(user_id)
            )
            return
        
        # پیام تایید برای کاربر
        await update.message.reply_text(
            f"✅ {file_type} رسید شارژ شما دریافت شد!\n\nبزودی مبلغ واریزی به حساب کاربرتون اضافه میشود!\n\n📊 ارسال شده برای: {sent_count} مدیر",
            reply_markup=main_menu(user_id)
        )
        
        # ذخیره در state برای تایید/رد توسط ادمین
        user_states[user_id] = {
            'charge_pending_approval': True,
            'charge_amount': user_state['charge_amount'],
            'receipt_type': file_type
        }
        
        return

    # مدیریت حذف کد تخفیف جدید توسط ادمین
    if user_state.get('waiting_for_new_discount_removal') and user_id in ADMIN_IDS:
        try:
            discount_number = int(message_text.strip())
            available_codes = user_state.get('available_codes', [])
            
            if discount_number < 1 or discount_number > len(available_codes):
                await update.message.reply_text(
                    f"❌ شماره کد تخفیف نامعتبر است! لطفاً عددی بین 1 تا {len(available_codes)} وارد کنید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]])
                )
            else:
                # حذف کد تخفیف
                code_to_remove, code_info = available_codes[discount_number - 1]
                category = code_info.get('category', 'نامشخص')
                
                del discount_codes[code_to_remove]
                save_user_data()
                
                await update.message.reply_text(
                    f"✅ کد تخفیف '{code_to_remove}' با موفقیت حذف شد!\n\n📦 بخش: {category}\n📊 تخفیف: {code_info['discount']}%",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]])
                )
        except ValueError:
            await update.message.reply_text(
                "❌ لطفاً شماره کد تخفیف را به صورت عدد وارد کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]])
            )
        
        del user_states[user_id]
        return

    # مدیریت ساخت کد تخفیف جدید توسط ادمین
    if user_state.get('waiting_for_new_discount_code') and user_id in ADMIN_IDS:
        # دریافت کد تخفیف جدید
        code_name = message_text.strip().upper()
        discount_category = user_state.get('discount_category', 'نامشخص')
        
        # بررسی صحت نام کد
        if not code_name or len(code_name) < 3:
            await update.message.reply_text(
                "❌ نام کد تخفیف خیلی کوتاه است!\n\nلطفاً کد حداقل 3 کاراکتر وارد کنید.\n\nمثال: KIAYT10, ali20",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="add_new_discount_code")]])
            )
            return
        
        # بررسی تکراری نبودن کد
        if code_name in discount_codes:
            await update.message.reply_text(
                f"❌ کد تخفیف '{code_name}' قبلاً وجود دارد!\n\nلطفاً نام دیگری انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="add_new_discount_code")]])
            )
            return
        
        # استخراج درصد تخفیف از کد
        discount_percentage = extract_discount_percentage(code_name)
        if discount_percentage == 0:
            await update.message.reply_text(
                f"❌ نمی‌توان درصد تخفیف را از کد '{code_name}' استخراج کرد!\n\nلطفاً کدی وارد کنید که در آخر آن عدد باشد.\n\nمثال: KIAYT10, ali20",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="add_new_discount_code")]])
            )
            return
        
        # ساخت کد تخفیف جدید
        discount_codes[code_name] = {
            'discount': discount_percentage,
            'category': discount_category
        }
        
        save_user_data()
        
        await update.message.reply_text(
            f"✅ کد تخفیف با موفقیت ساخته شد!\n\n🎫 نام کد: {code_name}\n📊 درصد تخفیف: {discount_percentage}% (از کد استخراج شد)\n📦 بخش: {discount_category}\n\nکاربران اکنون می‌توانند از این کد تخفیف استفاده کنند! 🎉",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="discount_codes_panel")]])
        )
        
        del user_states[user_id]
        return

    # پردازش رسید تمدید کارت به کارت
    if user_state.get('waiting_for_extension_receipt'):
        extension_code = user_state.get('extension_code', '')
        product_name = user_state.get('product_name', '')
        extension_price = user_state.get('extension_price', 0)
        
        # ارسال پیام تایید به کاربر
        await update.message.reply_text(
            f"✅ رسید تمدید شما دریافت شد!\n\n🔄 محصول: {product_name}\n💰 مبلغ: {extension_price:,} تومان\n🎫 کد تمدید: {extension_code}\n\nدرخواست تمدید شما در اسرع وقت بررسی خواهد شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        
        # ارسال اطلاعات تمدید برای مدیران
        if update.message.photo:
            file_type = "🖼️ عکس"
        elif update.message.document:
            file_type = "📄 فایل"
        else:
            file_type = "📝 متن"
            
        extension_text = f"""🔄 درخواست تمدید جدید (کارت به کارت)

👤 کاربر: {update.effective_user.first_name or 'نامشخص'}
🆔 آیدی: {user_id}
👤 نام کاربری: @{update.effective_user.username or 'ندارد'}

🔄 محصول: {product_name}
💰 مبلغ: {extension_price:,} تومان
🎫 کد تمدید: {extension_code}
📎 نوع رسید: {file_type}

💳 روش پرداخت: کارت به کارت"""
        
        # دکمه‌های مدیریت برای مدیران
        admin_keyboard = [
            [InlineKeyboardButton("✅ تایید تمدید", callback_data=f"approve_extension_{user_id}_{extension_code}")],
            [InlineKeyboardButton("❌ رد تمدید", callback_data=f"reject_extension_{user_id}_{extension_code}")],
            [InlineKeyboardButton("💬 پاسخ به کاربر", callback_data=f"reply_to_{user_id}")]
        ]
        
        # ارسال برای همه مدیران
        for admin_id in ADMIN_IDS:
            try:
                if update.message.photo:
                    await context.bot.send_photo(
                        admin_id,
                        update.message.photo[-1].file_id,
                        caption=extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        admin_id,
                        update.message.document.file_id,
                        caption=extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
                else:
                    await context.bot.send_message(
                        admin_id,
                        extension_text,
                        reply_markup=InlineKeyboardMarkup(admin_keyboard)
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به مدیر {admin_id}: {e}")
        
        # غیرفعال کردن کد تمدید
        if extension_code in extension_codes:
            extension_codes[extension_code]['valid'] = False
            save_user_data()
        
        del user_states[user_id]
        return

    # ساخت کد تمدید توسط مدیر
    if user_state.get('creating_extension_code') and user_id in ADMIN_IDS:
        step = user_state.get('step', '')
        
        if step == 'extension_code':
            # دریافت کد تمدید
            extension_code = message_text.strip().upper()
            
            if not extension_code:
                await update.message.reply_text(
                    "❌ کد تمدید نمی‌تواند خالی باشد! لطفاً کد تمدید را وارد کنید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_create_extension_code")]])
                )
                return
            
            # بررسی عدم تکرار کد
            if extension_code in extension_codes:
                await update.message.reply_text(
                    "❌ این کد تمدید قبلاً استفاده شده است! لطفاً کد جدید وارد کنید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_create_extension_code")]])
                )
                return
                
            user_state['extension_code'] = extension_code
            user_state['step'] = 'price'
            
            extension_price = user_state.get('extension_price', 0)
            product_name = user_state.get('extension_product_name', '')
            
            text = f"2️⃣ کد تمدید \'{extension_code}\' برای محصول {product_name} ساخته خواهد شد.\n\n💰 قیمت پیش‌فرض: {extension_price:,} تومان\n\nلطفاً قیمت تمدید را وارد کنید (یا enter بزنید تا قیمت پیش‌فرض استفاده شود):"
            
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_create_extension_code")]])
            )
            return
        
        elif step == 'price':
            # دریافت قیمت
            if message_text.strip():
                try:
                    new_price = int(message_text.strip())
                    user_state['extension_price'] = new_price
                except ValueError:
                    await update.message.reply_text(
                        "❌ قیمت وارد شده نامعتبر است! لطفاً عدد صحیح وارد کنید.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_create_extension_code")]])
                    )
                    return
            
            # استفاده از کد تمدید وارد شده توسط مدیر
            extension_code = user_state.get('extension_code', '')
            
            # ذخیره کد تمدید
            extension_info = {
                'product': user_state['extension_product'],
                'price': user_state['extension_price'],
                'valid': True,
                'created_by': user_id,
                'created_at': datetime.now().isoformat()
            }
            
            if user_state.get('target_user_id'):
                extension_info['user_id'] = user_state['target_user_id']
            
            extension_codes[extension_code] = extension_info
            save_user_data()
            
            # پیام تایید
            product_name = user_state.get('extension_product_name', '')
            extension_price = user_state.get('extension_price', 0)
            
            success_text = f"""✅ کد تمدید با موفقیت ساخته شد!

🎫 کد تمدید: {extension_code}
📦 محصول: {product_name}
💰 قیمت: {extension_price:,} تومان

کد تمدید آماده استفاده است! 🎉"""
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل تمدید", callback_data="admin_extension")]])
            )
            
            del user_states[user_id]
            return

    # اعتبارسنجی کد تمدید
    if user_state.get('waiting_for_extension_code'):
        await process_extension_code(update, context)
        return

    # اعمال کد تخفیف
    if user_state.get('waiting_for_discount_code'):
        await apply_discount_code(update, context)
        return

# پردازش کد تمدید
async def process_extension_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش و اعتبارسنجی کد تمدید"""
    if not update.message or not update.effective_user:
        return
        
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    # بررسی وجود کد تمدید
    if code not in extension_codes:
        await update.message.reply_text(
            "❌ کد تمدید وارد شده معتبر نیست!\n\nلطفاً کد صحیح را از مالک دریافت کنید و دوباره وارد کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        del user_states[user_id]
        return
    
    # دریافت اطلاعات کد تمدید
    ext_info = extension_codes[code]
    
    # بررسی معتبر بودن کد
    if not ext_info.get('valid', False):
        await update.message.reply_text(
            "❌ این کد تمدید قبلاً استفاده شده یا منقضی شده است!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        del user_states[user_id]
        return
    
    # بررسی تطابق کاربر (اگر کد برای کاربر خاص باشه)
    if 'user_id' in ext_info and ext_info['user_id'] != user_id:
        await update.message.reply_text(
            "❌ این کد تمدید متعلق به کاربر دیگری است!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        del user_states[user_id]
        return
    
    # دریافت اطلاعات محصول
    product_key = ext_info.get('product', '')
    if product_key not in PRODUCTS:
        await update.message.reply_text(
            "❌ محصول مربوط به این کد تمدید یافت نشد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]])
        )
        del user_states[user_id]
        return
    
    product = PRODUCTS[product_key]
    extension_price = ext_info.get('price', product['price'] // 2)  # قیمت تمدید نصف قیمت اصلی
    
    # ذخیره اطلاعات تمدید برای کاربر
    user_states[user_id] = {
        'extension_pending': True,
        'extension_code': code,
        'product_key': product_key,
        'product_name': product['name'],
        'extension_price': extension_price,
        'original_price': product['price']
    }
    
    # نمایش فاکتور تمدید
    invoice_text = f"""✅ کد تمدید معتبر است!

🔄 فاکتور تمدید:
📦 محصول: {product['name']}
💰 قیمت اصلی: {product['price']:,} تومان
🔄 قیمت تمدید: {extension_price:,} تومان
📱 کد محصول: {product['code']}
🎫 کد تمدید: {code}

💡 برای تمدید محصول خود، یکی از روش‌های پرداخت زیر را انتخاب کنید:"""
    
    keyboard = [
        [InlineKeyboardButton("💳 کارت به کارت", callback_data=f"extension_payment_{code}")],
        [InlineKeyboardButton("💰 کسر از موجودی", callback_data=f"extension_balance_{code}")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(invoice_text, reply_markup=InlineKeyboardMarkup(keyboard))

# main function
def main():
    """راه‌اندازی ربات"""
    if not TOKEN:
        print("❌ خطا: TELEGRAM_BOT_TOKEN تنظیم نشده است!")
        return
    
    # بارگذاری داده‌ها
    load_user_data()
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_admin_reply))  # Handler برای ریپلای مدیران
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(MessageHandler(filters.PHOTO, handle_text_messages))
    application.add_handler(MessageHandler(filters.VIDEO, handle_text_messages))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_text_messages))
    
    print("🤖 ربات تلگرام راه‌اندازی شد...")
    print(f"👥 مدیران: {ADMIN_IDS}")
    print(f"📺 چنل: {CHANNEL_USERNAME}")
    
    # راه‌اندازی ربات
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()