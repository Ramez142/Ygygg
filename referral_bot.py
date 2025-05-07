import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import string
import os
import json

# --- CONFIGURATION ---
BOT_TOKEN = "8017598039:AAHe9-YG9b961QmHEadXa5y6oDe6oJ8DU-Y"
CHANNEL_USERNAME = "@OzUSDTT" # The bot will check if the user is a member of this channel
ADMIN_USER_ID = 0 # Optional: Set your Telegram User ID if you want admin commands

# --- DATA STORAGE ---
USER_DATA_FILE = "user_data.json"
# Structure of user_data:
# {
#   "user_id_str": {
#     "referred_by": "referrer_id_str" | None,
#     "referrals_made_count": 0,
#     "captcha_solved": False,
#     "joined_channel": False,
#     "referral_link_generated": False
#   }
# }
pending_captcha = {}  # user_id: correct_captcha_text
user_states = {} # user_id: current_state (e.g., "awaiting_captcha", "awaiting_channel_join")

bot = telebot.TeleBot(BOT_TOKEN)

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

users_data = load_user_data()

# --- CAPTCHA GENERATION ---
def generate_captcha_text(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text):
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            # Try to find any .ttf font as a fallback
            font_paths = [os.path.join(dp, f) for dp, dn, fn in os.walk("/usr/share/fonts") for f in fn if f.endswith('.ttf')]
            if font_paths:
                font_path = random.choice(font_paths)
                print(f"تحذير: خط DejaVuSans-Bold.ttf غير موجود، تم استخدام الخط البديل: {font_path}")
            else:
                print("خطأ: لم يتم العثور على أي خطوط .ttf في /usr/share/fonts. لا يمكن إنشاء الكابتشا بالخطوط.")
                return None
        font_size = random.randint(35, 45)
        font = ImageFont.truetype(font_path, font_size)
    except IOError as e:
        print(f"خطأ في تحميل الخط: {e}. لا يمكن إنشاء الكابتشا.")
        return None

    # Calculate text size accurately
    try:
        text_bbox = draw.textbbox((0,0), text, font=font) # Requires draw object first
        # temp image to get bbox
        temp_image = Image.new("RGB", (1,1))
        temp_draw = ImageDraw.Draw(temp_image)
        text_bbox = temp_draw.textbbox((0,0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except Exception:
        # Fallback if textbbox fails (e.g. older Pillow)
        text_width = len(text) * (font_size // 2) # Rough estimate
        text_height = font_size

    image_width = text_width + 40 # Add padding
    image_height = text_height + 30 # Add padding
    image = Image.new("RGB", (image_width, image_height), color="white")
    draw = ImageDraw.Draw(image)

    # Draw text with some variation
    char_x_pos = 20 # Start x position for text
    for char_index, char_val in enumerate(text):
        # Calculate position for each character to center it better vertically
        try:
            char_bbox = draw.textbbox((0,0), char_val, font=font)
            char_width = char_bbox[2] - char_bbox[0]
            char_height = char_bbox[3] - char_bbox[1]
        except Exception:
            char_width = font_size // 2
            char_height = font_size
        
        text_x = char_x_pos + random.randint(-2, 2)
        text_y = (image_height - char_height) // 2 + random.randint(-3, 3) # Center vertically
        draw.text((text_x, text_y), char_val, fill=(random.randint(0,100), random.randint(0,100), random.randint(0,100)), font=font)
        char_x_pos += char_width + random.randint(0,3) # Advance x position

    # Add noise (lines and points) - Medium difficulty
    for _ in range(random.randint(5, 10)):
        x1, y1 = random.randint(0, image_width), random.randint(0, image_height)
        x2, y2 = random.randint(0, image_width), random.randint(0, image_height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100,200), random.randint(100,200), random.randint(100,200)), width=random.randint(1,2))

    for _ in range(random.randint(80, 150)):
        x, y = random.randint(0, image_width - 1), random.randint(0, image_height - 1)
        draw.point((x, y), fill=(random.randint(120,200), random.randint(120,200), random.randint(120,200)))

    image = image.filter(ImageFilter.GaussianBlur(radius=0.7))

    captcha_image_path = "captcha.png"
    image.save(captcha_image_path)
    return captcha_image_path

# --- BOT HANDLERS ---
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    
    if user_id not in users_data:
        users_data[user_id] = {
            "referred_by": None,
            "referrals_made_count": 0,
            "captcha_solved": False,
            "joined_channel": False,
            "referral_link_generated": False
        }

    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and referrer_id != user_id and referrer_id in users_data:
            if users_data[user_id]["referred_by"] is None:
                users_data[user_id]["referred_by"] = referrer_id
                if "referrals_made_count" not in users_data[referrer_id]:
                     users_data[referrer_id]["referrals_made_count"] = 0
                users_data[referrer_id]["referrals_made_count"] += 1
                bot.send_message(chat_id, f"لقد تم تسجيل إحالتك عن طريق المستخدم صاحب المعرف: {referrer_id}. شكراً!")
                try:
                    bot.send_message(referrer_id, f"🎉 مستخدم جديد ({message.from_user.first_name}) انضم عن طريق رابط إحالتك!")
                except Exception as e:
                    print(f"فشل في إعلام المُحيل {referrer_id}: {e}")
        save_user_data(users_data)

    if users_data[user_id].get("captcha_solved", False):
        if users_data[user_id].get("joined_channel", False):
            send_welcome_and_referral_link(chat_id, user_id)
        else:
            check_channel_membership(chat_id, user_id, message)
        return

    captcha_text = generate_captcha_text()
    captcha_image_file = generate_captcha_image(captcha_text)

    if captcha_image_file:
        pending_captcha[user_id] = captcha_text
        user_states[user_id] = "awaiting_captcha"
        try:
            with open(captcha_image_file, "rb") as photo:
                bot.send_photo(chat_id, photo, caption="أهلاً بك! 👋\nللمتابعة، يرجى إدخال النص الموجود في الصورة للتحقق (الكابتشا).")
        except Exception as e:
            bot.send_message(chat_id, "عذراً، حدث خطأ أثناء إرسال صورة الكابتشا. يرجى المحاولة مرة أخرى لاحقاً أو التواصل مع الأدمن.")
            print(f"خطأ في إرسال صورة الكابتشا: {e}")
        finally:
            if os.path.exists(captcha_image_file):
                os.remove(captcha_image_file)
    else:
        bot.send_message(chat_id, "عذراً، لم نتمكن من إنشاء الكابتشا في الوقت الحالي بسبب مشكلة في الخطوط. يرجى المحاولة مرة أخرى لاحقاً أو إبلاغ الأدمن.")

def check_channel_membership(chat_id, user_id_str, original_message_for_start=None):
    user_id_int = int(user_id_str)
    try:
        member_status = bot.get_chat_member(CHANNEL_USERNAME, user_id_int).status
        if member_status in ["member", "administrator", "creator"]:
            users_data[user_id_str]["joined_channel"] = True
            save_user_data(users_data)
            bot.send_message(chat_id, "شكراً لانضمامك للقناة! 🎉")
            send_welcome_and_referral_link(chat_id, user_id_str)
            user_states.pop(user_id_str, None) # Clear state
        else:
            send_join_channel_prompt(chat_id, user_id_str)
    except Exception as e:
        print(f"خطأ في التحقق من عضوية القناة للمستخدم {user_id_str} في {CHANNEL_USERNAME}: {e}")
        bot.send_message(chat_id, f"لم أتمكن من التحقق من عضويتك في القناة {CHANNEL_USERNAME} حالياً. تأكد أن البوت لديه الصلاحيات اللازمة أو أن القناة عامة.")
        send_join_channel_prompt(chat_id, user_id_str)

def send_join_channel_prompt(chat_id, user_id):
    markup = types.InlineKeyboardMarkup()
    channel_link_button = types.InlineKeyboardButton(text=f"🔗 الانضمام إلى {CHANNEL_USERNAME.replace('@','')}", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
    check_join_button = types.InlineKeyboardButton(text="✅ لقد انضممت، تحقق الآن", callback_data=f"checkjoin_{user_id}")
    markup.add(channel_link_button)
    markup.add(check_join_button)
    bot.send_message(chat_id, f"للحصول على رابط الإحالة الخاص بك، يرجى أولاً الانضمام إلى قناتنا: {CHANNEL_USERNAME}", reply_markup=markup)
    user_states[user_id] = "awaiting_channel_join"

@bot.callback_query_handler(func=lambda call: call.data.startswith("checkjoin_"))
def callback_check_join(call):
    user_id_to_check = call.data.split("_")[1]
    chat_id = call.message.chat.id

    if str(call.from_user.id) != user_id_to_check:
        bot.answer_callback_query(call.id, "هذا الزر ليس لك.")
        return

    bot.answer_callback_query(call.id, "جاري التحقق من انضمامك...")
    # Pass the original message context if available, or None
    check_channel_membership(chat_id, user_id_to_check, original_message_for_start=call.message)

def send_welcome_and_referral_link(chat_id, user_id):
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    users_data[user_id]["referral_link_generated"] = True
    save_user_data(users_data)

    welcome_message = (
        f"أهلاً بك مجدداً! لقد تحققت بنجاح.\n\n"
        f"💰 رابط الإحالة الخاص بك هو:\n`{referral_link}`\n\n"
        f"شارك هذا الرابط مع أصدقائك. ستحصل على مكافأة (سيتم تحديدها لاحقاً) عن كل شخص ينضم عبر رابطك ويقوم بالتحقق.\n\n"
        f"عدد الأشخاص الذين دعوتهم بنجاح: {users_data[user_id].get('referrals_made_count', 0)}"
    )
    bot.send_message(chat_id, welcome_message, parse_mode="Markdown")
    user_states.pop(user_id, None) # Clear state

@bot.message_handler(func=lambda message: user_states.get(str(message.from_user.id)) == "awaiting_captcha")
def handle_captcha_input(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id

    if user_id in pending_captcha:
        correct_captcha = pending_captcha[user_id]
        user_input = message.text.strip().upper()

        if user_input == correct_captcha:
            bot.send_message(chat_id, "✅ الكابتشا صحيحة!")
            users_data[user_id]["captcha_solved"] = True
            save_user_data(users_data)
            del pending_captcha[user_id]
            check_channel_membership(chat_id, user_id, original_message_for_start=message)
        else:
            bot.send_message(chat_id, "❌ الكابتشا غير صحيحة. حاول مرة أخرى أو اضغط /start للحصول على كابتشا جديدة.")
            # Optionally resend a new captcha immediately:
            # handle_start(message) # This could lead to loops if not careful, better to guide user
    else:
        bot.send_message(chat_id, "لم أجد كابتشا معلقة لك. جرب /start")

@bot.message_handler(commands=["myreferrals"])
def handle_my_referrals(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id

    if user_id in users_data and users_data[user_id].get("referral_link_generated"):
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        count = users_data[user_id].get("referrals_made_count", 0)
        bot.send_message(chat_id, f"رابط الإحالة الخاص بك: `{referral_link}`\nعدد الإحالات الناجحة: {count}", parse_mode="Markdown")
    elif user_id in users_data and not users_data[user_id].get("captcha_solved"):
        bot.send_message(chat_id, "يجب عليك حل الكابتشا أولاً. اضغط /start")
    elif user_id in users_data and not users_data[user_id].get("joined_channel"):
        bot.send_message(chat_id, f"يجب عليك الانضمام إلى القناة {CHANNEL_USERNAME} أولاً. اضغط /start للمتابعة.")
    else:
        bot.send_message(chat_id, "لم أجد بيانات لك أو لم يتم إنشاء رابط إحالتك بعد. اضغط /start للبدء.")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    user_id = str(message.from_user.id)
    current_state = user_states.get(user_id)

    if current_state == "awaiting_captcha":
        # This should be caught by handle_captcha_input, but as a fallback:
        bot.send_message(message.chat.id, "يرجى إدخال الكابتشا أو اضغط /start للحصول على واحدة جديدة.")
        return
    if current_state == "awaiting_channel_join":
        bot.send_message(message.chat.id, f"يرجى استخدام الأزرار للانضمام إلى القناة والتحقق، أو اضغط /start إذا واجهت مشكلة.")
        return

    bot.send_message(message.chat.id, "مرحباً! استخدم الأمر /start لبدء التفاعل مع البوت والحصول على رابط الإحالة الخاص بك.")

if __name__ == "__main__":
    print("البوت بدأ التشغيل...")
    try:
        save_user_data(users_data) # Test initial save
    except Exception as e:
        print(f"تنبيه حرج: لم يتمكن من الكتابة إلى {USER_DATA_FILE}. يرجى التحقق من الأذونات. الخطأ: {e}")
        # exit(1) # Don't exit in sandbox, just print error
    
    try:
        bot_info = bot.get_me()
        print(f"معرف البوت: {bot_info.id}, اسم مستخدم البوت: {bot_info.username}")
    except Exception as e:
        print(f"تنبيه حرج: فشل الاتصال بـ Telegram API. تحقق من BOT_TOKEN. الخطأ: {e}")
        # exit(1) # Don't exit in sandbox

    bot.polling(none_stop=True, timeout=60, long_polling_timeout = 50)

