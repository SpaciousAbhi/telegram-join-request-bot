import re

def to_bold(text: str) -> str:
    """
    Converts English letters (A-Z, a-z) and numbers (0-9) in a string
    to their bold Unicode sans-serif equivalents (e.g. A -> 𝗔, a -> 𝗮, 0 -> 𝟬).
    Leaves HTML tags, invite links, usernames, and other languages intact.
    """
    if not text:
        return ""
    
    # We want to avoid converting HTML tags (like <a href="..."> or <b>) and telegram entity markers (like t.me/... or @username).
    # Let's write a token-based replacer that skips HTML tags, links, and usernames.
    
    pattern = re.compile(
        r'(<[^>]+>|https?://\S+|t\.me/\S+|@\w+)', 
        re.IGNORECASE
    )
    
    tokens = pattern.split(text)
    
    def bold_char(char: str) -> str:
        o = ord(char)
        if 65 <= o <= 90:    # A-Z -> Bold Sans-serif A-Z (Starts at U+1D5D4)
            return chr(o + 0x1D5D4 - 65)
        elif 97 <= o <= 122:  # a-z -> Bold Sans-serif a-z (Starts at U+1D5EE)
            return chr(o + 0x1D5EE - 97)
        elif 48 <= o <= 57:   # 0-9 -> Bold Sans-serif 0-9 (Starts at U+1D7EC)
            return chr(o + 0x1D7EC - 48)
        return char

    def bold_token(token: str) -> str:
        # If it is a tag, link, or username, return as is
        if token.startswith('<') and token.endswith('>'):
            return token
        if token.lower().startswith('http://') or token.lower().startswith('https://') or token.lower().startswith('t.me/'):
            return token
        if token.startswith('@'):
            return token
        
        # Otherwise, translate character by character
        return "".join(bold_char(c) for c in token)

    return "".join(bold_token(tok) for tok in tokens)

# Translation Dictionaries
STRINGS = {
    "en": {
        "choose_lang": "𝗖𝗛𝗢𝗢𝗦𝗘 𝗬𝗢𝗨𝗥 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘",
        "btn_lang_en": "🇬🇧 𝗘𝗡𝗚𝗟𝗜𝗦𝗛",
        "btn_lang_hi": "🇮🇳 𝗛𝗜𝗡🇩🇮",
        "btn_lang_hinglish": "🇮🇳 𝗛𝗜𝗡𝗚𝗟𝗜𝗦𝗛",
        "btn_lang_ur": "🇵🇰 𝗨𝗥🇩🇺",
        
        "start_instruction": (
            "𝗝𝗨𝗦𝗧 𝗔𝗗𝗗 𝗧𝗛𝗜𝗦 𝗕𝗢𝗧 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 𝗢𝗥 𝗚𝗥𝗢𝗨𝗣 — 𝗡𝗘𝗪 𝗝𝗢𝗜𝗡 𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗦 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗔𝗖𝗖𝗘𝗣𝗧𝗘𝗗 𝗔𝗨𝗧𝗢𝗠𝗔𝗧𝗜𝗖𝗔𝗟𝗟𝗬.\n\n"
            "𝗩𝗘𝗡𝗢𝗠 𝗦𝗧𝗢𝗡𝗘 𝗡𝗘𝗧𝗪𝗢𝗥𝗞 — t.me/Venom_Stone_Network — Main Channel."
        ),
        
        "btn_add_channel": "➕ 𝗔𝗗𝗗 𝗧𝗢 𝗖𝗛𝗔𝗡𝗡𝗘𝗟",
        "btn_add_group": "➕ 𝗔𝗗𝗗 𝗧𝗢 𝗚𝗥𝗢𝗨𝗣",
        "btn_bulk_approve": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗘 𝗢𝗟𝗗 𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗦",
        "btn_my_chats": "📊 𝗠𝗬 𝗖𝗛𝗔𝗡𝗡𝗘𝗟𝗦 / 𝗚𝗥𝗢𝗨𝗣𝗦",
        "btn_support": "🔗 𝗝𝗢𝗜𝗡 𝗩𝗘𝗡𝗢𝗠 𝗦𝗧𝗢𝗡𝗘 𝗡𝗘𝗧𝗪𝗢𝗥𝗞",
        
        "fsub_title": "📢 𝗙𝗢𝗥𝗖𝗘 𝗦𝗨𝗕𝗦𝗖𝗥𝗜𝗣𝗧𝗜𝗢𝗡 𝗥𝗘𝗤𝗨𝗜𝗥𝗘𝗗",
        "fsub_msg": "𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗷𝗼𝗶𝗻 or send request to 𝘁𝗵𝗲 𝗳𝗼𝗹𝗹𝗼𝘄𝗶𝗻𝗴 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀/𝗴𝗿𝗼𝘂𝗽𝘀 𝘁𝗼 𝘂𝗻𝗹𝗼𝗰𝗸 𝘁𝗵𝗲 𝗯𝗼𝘁:",
        "fsub_joined_btn": "🔄 𝗖𝗛𝗘𝗖𝗞 𝗝𝗢𝗜𝗡𝗘𝗗",
        "fsub_please_join": "❌ 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗻𝗼𝘁 𝗷𝗼𝗶𝗻𝗲𝗱 𝗮𝗹𝗹 𝗿𝗲𝗾𝘂𝗶𝗿𝗲𝗱 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝘆𝗲𝘁. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗷𝗼𝗶𝗻 𝘁𝗵𝗲𝗺 𝗳𝗶𝗿𝘀𝘁.",
        
        "verify_msg": "𝗛𝗲𝗹𝗹𝗼, 𝘆𝗼𝘂 𝗿𝗲𝗾𝘂𝗲𝘀𝘁𝗲𝗱 𝘁𝗼 𝗷𝗼𝗶𝗻 {chat_title}.\n𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗲 𝘆𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮 𝗿𝗼𝗯𝗼𝘁 𝘁𝗼 𝗴𝗲𝘁 𝗮𝗰𝗰𝗲𝘀𝘀.",
        "verify_btn": "✅ 𝗜'𝗠 𝗡𝗢𝗧 𝗔 𝗥𝗢𝗕𝗢𝗧",
        "verify_success": "✅ 𝗬𝗼𝘂 𝗮𝗿𝗲 𝘃𝗲𝗿𝗶𝗳𝗶𝗲𝗱 𝗻𝗼𝘄. 𝗬𝗼𝘂𝗿 𝗿𝗲𝗾𝘂𝗲𝘀𝘁 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗰𝗰𝗲𝗽𝘁𝗲𝗱. 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗻𝗼𝘄 𝗼𝗽𝗲𝗻 {chat_title}.",
        
        "no_chats": "📊 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗻𝗼𝘁 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝗮𝗻𝘆 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗼𝗿 𝗴𝗿𝗼𝘂𝗽𝘀 𝘆𝗲𝘁. Add this bot as admin to your chat to start.",
        "chat_list_title": "📊 𝗬𝗢𝗨𝗥 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗 𝗖𝗛𝗔𝗧𝗦",
        
        "chat_report_title": "🎉 𝗖𝗛𝗔𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗!",
        "chat_report_details": (
            "📝 𝗡𝗮𝗺𝗲: {chat_title}\n"
            "🆔 𝗜𝗗: <code>{chat_id}</code>\n"
            "🏷️ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: {username}\n"
            "👤 𝗧𝘆𝗽𝗲: {chat_type}\n"
            "👥 𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {member_count}\n"
            "🛡️ 𝗔𝗱𝗺𝗶𝗻 𝗦𝘁𝗮𝘁𝘂𝘀: {admin_status}\n"
            "⚙️ 𝗣𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻𝘀: {permissions_status}\n"
            "🤖 𝗔𝘂𝘁𝗼-𝗔𝗽𝗽𝗿𝗼𝘃𝗲: {auto_approve_status}"
        ),
        
        "chat_settings_title": "⚙️ 𝗖𝗛𝗔𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧: {chat_title}",
        "btn_auto_approve_on": "🟢 𝗔𝗨𝗧𝗢-𝗔𝗣𝗣𝗥𝗢𝗩𝗘: 𝗢𝗡",
        "btn_auto_approve_off": "🔴 𝗔𝗨𝗧𝗢-𝗔𝗣𝗣𝗥𝗢𝗩𝗘: 𝗢𝗙𝗙",
        "btn_bulk_approve_this": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗘",
        "btn_remove_chat": "❌ 𝗥𝗘𝗠𝗢𝗩𝗘 / 𝗗𝗘𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘",
        "btn_back": "⬅️ 𝗕𝗔𝗖𝗞",
        "btn_home": "🏠 𝗛𝗢𝗠𝗘",
        
        "confirm_remove": "⚠️ 𝗔𝗿𝗲 𝘆𝗼𝘂 𝘀𝘂𝗿𝗲 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗿𝗲𝗺𝗼𝘃𝗲 {chat_title}?",
        "btn_confirm_yes": "✅ 𝗬𝗘𝗦, 𝗥𝗘𝗠𝗢𝗩𝗘",
        "btn_confirm_no": "❌ 𝗡𝗢, 𝗖𝗔𝗡𝗖𝗘𝗟",
        
        "bulk_no_chats": "❌ 𝗬𝗼𝘂 𝗺𝘂𝘀𝘁 𝗰𝗼𝗻𝗻𝗲𝗰𝘁 𝗮 𝗰𝗵𝗮𝗻𝗻𝗲𝗹/𝗴𝗿𝗼𝘂𝗽 𝗳𝗶𝗿𝘀𝘁 to use Bulk Approval.",
        "bulk_select_chat": "⚡ 𝗦𝗘𝗟𝗘𝗖𝗧 𝗖𝗛𝗔𝗧 𝗙𝗢𝗥 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗔𝗟",
        
        "bulk_status_title": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗔𝗟 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦: {chat_title}",
        "bulk_status_msg": (
            "📊 𝗦𝘁𝗮𝘁𝘂𝘀: {status_icon} {status}\n"
            "📈 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀: {progress_pct}%\n"
            "📥 𝗧𝗼𝘁𝗮𝗹 𝗣𝗲𝗻𝗱𝗶𝗻𝗴: {total}\n"
            "✅ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {approved}\n"
            "❌ 𝗙𝗮𝗶𝗹𝗲𝗱: {failed}\n"
            "⏭️ 𝗦𝗸𝗶𝗽𝗽𝗲𝗱: {skipped}\n"
            "⏳ 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴: {remaining}\n"
            "🚀 𝗦𝗽𝗲𝗲𝗱: {speed} req/min"
        ),
        "btn_pause": "⏸️ 𝗣𝗔𝗨𝗦𝗘",
        "btn_resume": "▶️ 𝗥𝗘𝗦𝗨𝗠𝗘",
        "btn_stop": "⛔ 𝗦𝗧𝗢𝗣",
        "btn_refresh": "🔄 𝗥𝗘𝗙𝗥𝗘𝗦𝗛",
        
        "bulk_started": "⚡ Bulk approval started for {chat_title}.",
        "bulk_paused": "⏸️ Bulk approval paused.",
        "bulk_resumed": "▶️ Bulk approval resumed.",
        "bulk_stopped": "⛔ Bulk approval stopped.",
        "bulk_completed": "🎉 Bulk approval completed successfully!",
        
        "permission_missing_warning": "⚠️ 𝗠𝗶𝘀𝘀𝗶𝗻𝗴 Required Admin Permission: <b>Invite Users via Link / Approve Join Requests</b>. Please enable this to allow auto-approval.",
        "admin_active": "🟢 𝗔𝗗𝗠𝗜𝗡 𝗔𝗖𝗧𝗜𝗩𝗘",
        "admin_inactive": "🔴 𝗡𝗢𝗧 𝗔𝗗𝗠𝗜𝗡 / 𝗟𝗢𝗦𝗧 𝗥𝗜𝗚𝗛𝗧𝗦",
        "active": "🟢 𝗔𝗖𝗧𝗜𝗩𝗘",
        "inactive": "🔴 𝗜𝗡𝗔𝗖𝗧𝗜𝗩𝗘",
        
        "general_settings_title": "⚙️ 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦",
        "btn_change_lang": "🌐 𝗖𝗛𝗔𝗡𝗚𝗘 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘",
    },
    
    "hi": {
        "choose_lang": "𝗖𝗛𝗢𝗢𝗦𝗘 𝗬𝗢𝗨𝗥 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘 / अपनी भाषा चुनें",
        "btn_lang_en": "🇬🇧 𝗘𝗡𝗚𝗟𝗜𝗦𝗛",
        "btn_lang_hi": "🇮🇳 𝗛🇮🇳𝗗🇮",
        "btn_lang_hinglish": "🇮🇳 𝗛🇮🇳𝗚𝗟🇮𝗦𝗛",
        "btn_lang_ur": "🇵🇰 𝗨𝗥🇩🇺",
        
        "start_instruction": (
            "बस इस बॉट को अपने चैनल या ग्रुप में जोड़ें — नए जॉइन अनुरोधों को स्वचालित रूप से स्वीकार कर लिया जाएगा।\n\n"
            "वीएनओएम स्टोन नेटवर्क — t.me/Venom_Stone_Network — मुख्य चैनल।"
        ),
        
        "btn_add_channel": "➕ चैनल में जोड़ें",
        "btn_add_group": "➕ ग्रुप में जोड़ें",
        "btn_bulk_approve": "⚡ पुराने अनुरोधों को एक साथ स्वीकार करें",
        "btn_my_chats": "📊 मेरे चैनल / ग्रुप",
        "btn_support": "🔗 वीएनओएम स्टोन नेटवर्क ज्वाइन करें",
        
        "fsub_title": "📢 अनिवार्य सदस्यता आवश्यक",
        "fsub_msg": "बॉट का उपयोग करने के लिए आपको निम्नलिखित चैनलों/ग्रुपों में शामिल होना या अनुरोध भेजना होगा:",
        "fsub_joined_btn": "🔄 सदस्यता जांचें",
        "fsub_please_join": "❌ आपने अभी तक सभी आवश्यक चैनलों को ज्वाइन नहीं किया है। कृपया पहले उन्हें ज्वाइन करें।",
        
        "verify_msg": "नमस्ते, आपने {chat_title} में शामिल होने का अनुरोध किया है।\nकृपया साबित करें कि आप रोबोट नहीं हैं।",
        "verify_btn": "✅ मैं रोबोट नहीं हूँ",
        "verify_success": "✅ आप सत्यापित हो चुके हैं। आपका अनुरोध स्वीकार कर लिया गया है। अब आप {chat_title} खोल सकते हैं।",
        
        "no_chats": "📊 आपने अभी तक कोई चैनल या ग्रुप नहीं जोड़ा है। शुरू करने के लिए इस बॉट को अपने चैट में एडमिन के रूप में जोड़ें।",
        "chat_list_title": "📊 आपके जुड़े हुए चैट",
        
        "chat_report_title": "🎉 चैट सफलतापूर्वक जुड़ गया है!",
        "chat_report_details": (
            "📝 नाम: {chat_title}\n"
            "🆔 आईडी: <code>{chat_id}</code>\n"
            "🏷️ यूजरनेम: {username}\n"
            "👤 प्रकार: {chat_type}\n"
            "👥 सदस्य: {member_count}\n"
            "🛡️ एडमिन स्थिति: {admin_status}\n"
            "⚙️ अनुमतियाँ स्थिति: {permissions_status}\n"
            "🤖 ऑटो-अस्वीकृति/स्वीकृति: {auto_approve_status}"
        ),
        
        "chat_settings_title": "⚙️ चैट प्रबंधन: {chat_title}",
        "btn_auto_approve_on": "🟢 ऑटो-अस्वीकृति/स्वीकृति: चालू",
        "btn_auto_approve_off": "🔴 ऑटो-अस्वीकृति/स्वीकृति: बंद",
        "btn_bulk_approve_this": "⚡ एक साथ स्वीकार करें",
        "btn_remove_chat": "❌ हटाएं / निष्क्रिय करें",
        "btn_back": "⬅️ वापस",
        "btn_home": "🏠 मुख्य मेनू",
        
        "confirm_remove": "⚠️ क्या आप वाकई {chat_title} को हटाना चाहते हैं?",
        "btn_confirm_yes": "✅ हाँ, हटाएं",
        "btn_confirm_no": "❌ नहीं, रद्द करें",
        
        "bulk_no_chats": "❌ बल्क स्वीकृति का उपयोग करने के लिए आपको पहले एक चैनल/ग्रुप जोड़ना होगा।",
        "bulk_select_chat": "⚡ बल्क स्वीकृति के लिए चैट चुनें",
        
        "bulk_status_title": "⚡ बल्क स्वीकृति प्रगति: {chat_title}",
        "bulk_status_msg": (
            "📊 स्थिति: {status_icon} {status}\n"
            "📈 प्रगति: {progress_pct}%\n"
            "📥 कुल लंबित: {total}\n"
            "✅ स्वीकृत: {approved}\n"
            "❌ विफल: {failed}\n"
            "⏭️ छोड़े गए: {skipped}\n"
            "⏳ शेष: {remaining}\n"
            "🚀 गति: {speed} req/min"
        ),
        "btn_pause": "⏸️ रोकें",
        "btn_resume": "▶️ फिर से शुरू करें",
        "btn_stop": "⛔ बंद करें",
        "btn_refresh": "🔄 ताज़ा करें",
        
        "bulk_started": "⚡ {chat_title} के लिए बल्क स्वीकृति शुरू हो गई है।",
        "bulk_paused": "⏸️ बल्क स्वीकृति रोक दी गई है।",
        "bulk_resumed": "▶️ बल्क स्वीकृति फिर से शुरू हो गई है।",
        "bulk_stopped": "⛔ बल्क स्वीकृति बंद कर दी गई है।",
        "bulk_completed": "🎉 बल्क स्वीकृति सफलतापूर्वक पूरी हो गई!",
        
        "permission_missing_warning": "⚠️ आवश्यक एडमिन अनुमति गायब है: <b>सदस्यों को आमंत्रित करें / शामिल होने के अनुरोधों को स्वीकार करें</b>। कृपया इसे सक्षम करें।",
        "admin_active": "🟢 एडमिन सक्रिय",
        "admin_inactive": "🔴 एडमिन निष्क्रिय / अधिकार खो दिए",
        "active": "🟢 सक्रिय",
        "inactive": "🔴 निष्क्रिय",
        
        "general_settings_title": "⚙️ सेटिंग्स",
        "btn_change_lang": "🌐 भाषा बदलें",
    },
    
    "hinglish": {
        "choose_lang": "𝗖𝗛𝗢𝗢𝗦𝗘 𝗬𝗢𝗨𝗥 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘",
        "btn_lang_en": "🇬🇧 𝗘𝗡𝗚𝗟𝗜𝗦𝗛",
        "btn_lang_hi": "🇮🇳 𝗛🇮🇳𝗗🇮",
        "btn_lang_hinglish": "🇮🇳 𝗛🇮🇳𝗚𝗟🇮𝗦𝗛",
        "btn_lang_ur": "🇵🇰 𝗨𝗥🇩🇺",
        
        "start_instruction": (
            "𝗝𝘂𝘀𝘁 𝗮𝗱𝗱 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁 𝘁𝗼 𝘆𝗼𝘂𝗿 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝗼𝗿 𝗴𝗿𝗼𝘂𝗽 — 𝗻𝗲𝘄 𝗷𝗼𝗶𝗻 𝗿𝗲𝗾𝘂𝗲𝘀𝘁𝘀 𝗮𝘂𝘁𝗼𝗺𝗮𝘁𝗶𝗰𝗮𝗹𝗹𝘆 𝗮𝗰𝗰𝗲𝗽𝘁 𝗵𝗼 𝗷𝗮𝘆𝗲𝗻𝗴𝗶.\n\n"
            "𝗩𝗘𝗡𝗢𝗠 𝗦𝗧𝗢𝗡𝗘 𝗡𝗘𝗧𝗪𝗢𝗥𝗞 — t.me/Venom_Stone_Network — Main Channel."
        ),
        
        "btn_add_channel": "➕ 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 𝗠𝗘 𝗔𝗗𝗗 𝗞𝗔𝗥𝗘𝗜𝗡",
        "btn_add_group": "➕ 𝗚𝗥𝗢𝗨𝗣 𝗠𝗘 𝗔𝗗𝗗 𝗞𝗔𝗥𝗘𝗜𝗡",
        "btn_bulk_approve": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗘 𝗢𝗟𝗗 𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗦",
        "btn_my_chats": "📊 𝗠𝗘𝗥𝗘 𝗖𝗛𝗔𝗡𝗡𝗘𝗟𝗦 / 𝗚𝗥𝗢𝗨𝗣𝗦",
        "btn_support": "🔗 𝗝𝗢𝗜𝗡 𝗩𝗘𝗡𝗢𝗠 𝗦𝗧𝗢𝗡𝗘 𝗡𝗘𝗧𝗪𝗢𝗥𝗞",
        
        "fsub_title": "📢 𝗙𝗢𝗥𝗖𝗘 𝗦𝗨𝗕𝗦𝗖𝗥𝗜𝗣𝗧𝗜𝗢𝗡 𝗥𝗘𝗤𝗨𝗜𝗥𝗘𝗗",
        "fsub_msg": "𝗕𝗼𝘁 𝘂𝘀𝗲 𝗸𝗮𝗿𝗻𝗲 𝗸𝗲 𝗹𝗶𝘆𝗲 𝗮𝗮𝗽𝗸𝗼 𝗶𝗻 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀/𝗴𝗿𝗼𝘂𝗽𝘀 𝗺𝗲 𝗷𝗼𝗶𝗻 𝘆𝗮 𝗿𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝗵𝗲𝗷𝗻𝗮 𝗵𝗼𝗴𝗮:",
        "fsub_joined_btn": "🔄 𝗖𝗛𝗘𝗖𝗞 𝗝𝗢𝗜𝗡𝗘𝗗",
        "fsub_please_join": "❌ 𝗔𝗮𝗽𝗻𝗲 𝘀𝗮𝗯𝗵𝗶 𝗿𝗲𝗾𝘂𝗶𝗿𝗲𝗱 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗷𝗼𝗶𝗻 𝗻𝗮𝗵𝗶 𝗸𝗶𝘆𝗲 𝗵𝗮𝗶𝗻. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗲𝗵𝗹𝗲 𝗷𝗼𝗶𝗻 𝗸𝗮𝗿𝗲𝗶𝗻.",
        
        "verify_msg": "𝗛𝗲𝗹𝗹𝗼, 𝗮𝗮𝗽𝗻𝗲 {chat_title} 𝗷𝗼𝗶𝗻 𝗸𝗮𝗿𝗻𝗲 𝗸𝗶 𝗿𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝗵𝗲𝗷𝗶 𝗵𝗮𝗶.\n𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗲 𝗸𝗮𝗿𝗲𝗶𝗻 𝗸𝗶 𝗮𝗮𝗽 𝗿𝗼𝗯𝗼𝘁 𝗻𝗮𝗵𝗶 𝗵𝗮𝗶𝗻.",
        "verify_btn": "✅ 𝗜'𝗠 𝗡𝗢𝗧 𝗔 𝗥𝗢𝗕𝗢𝗧",
        "verify_success": "✅ 𝗔𝗮𝗽 𝘃𝗲𝗿𝗶𝗳𝗶𝗲𝗱 𝗵𝗼 𝗴𝗮𝘆𝗲 𝗵𝗮𝗶𝗻. 𝗔𝗮𝗽𝗸𝗶 𝗿𝗲𝗾𝘂𝗲𝘀𝘁 𝗮𝗰𝗰𝗲𝗽𝘁 𝗵𝗼 𝗴𝗮𝘆𝗶 𝗵𝗮𝗶. 𝗔𝗯 𝗮𝗮𝗽 {chat_title} 𝗼𝗽𝗲𝗻 𝗸𝗮𝗿 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻.",
        
        "no_chats": "📊 𝗔𝗮𝗽𝗻𝗲 𝗸𝗼𝗶 𝗰𝗵𝗮𝗻𝗻𝗲𝗹 𝘆𝗮 𝗴𝗿𝗼𝘂𝗽 𝗰𝗼𝗻𝗻𝗲𝗰𝘁 𝗻𝗮𝗵𝗶 𝗸𝗶𝘆𝗮 𝗵𝗮𝗶. Bot ko admin banakar add karein.",
        "chat_list_title": "📊 𝗔𝗔𝗣𝗞𝗘 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗 𝗖𝗛𝗔𝗧𝗦",
        
        "chat_report_title": "🎉 𝗖𝗛𝗔𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗖𝗢𝗡𝗡𝗘𝗖𝗧𝗘𝗗!",
        "chat_report_details": (
            "📝 𝗡𝗮𝗺𝗲: {chat_title}\n"
            "🆔 𝗜Display ID: <code>{chat_id}</code>\n"
            "🏷️ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: {username}\n"
            "👤 𝗧𝘆𝗽𝗲: {chat_type}\n"
            "👥 𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {member_count}\n"
            "🛡️ 𝗔𝗱𝗺𝗶𝗻 𝗦𝘁𝗮𝘁𝘂𝘀: {admin_status}\n"
            "⚙️ 𝗣𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻𝘀: {permissions_status}\n"
            "🤖 𝗔𝘂𝘁𝗼-𝗔𝗽𝗽𝗿𝗼𝘃𝗲: {auto_approve_status}"
        ),
        
        "chat_settings_title": "⚙️ 𝗖𝗛𝗔𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗠𝗘𝗡𝗧: {chat_title}",
        "btn_auto_approve_on": "🟢 𝗔𝗨𝗧𝗼-𝗔𝗣𝗣𝗥𝗢𝗩𝗘: 𝗢𝗡",
        "btn_auto_approve_off": "🔴 𝗔𝗨𝗧𝗢-𝗔𝗣𝗣𝗥𝗢𝗩𝗘: 𝗢𝗙𝗙",
        "btn_bulk_approve_this": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗘",
        "btn_remove_chat": "❌ 𝗥𝗘𝗠𝗢𝗩𝗘 / 𝗗𝗘𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘",
        "btn_back": "⬅️ 𝗕𝗔𝗖𝗞",
        "btn_home": "🏠 𝗛𝗢𝗠𝗘",
        
        "confirm_remove": "⚠️ 𝗞𝘆𝗮 𝗮𝗮𝗽 {chat_title} 𝗸𝗼 𝗿𝗲𝗺𝗼𝘃𝗲 𝗸𝗮𝗿𝗻𝗮 𝗰𝗵𝗮𝗵𝘁𝗲 𝗵𝗮𝗶𝗻?",
        "btn_confirm_yes": "✅ 𝗛𝗔𝗔𝗡, 𝗥𝗘𝗠𝗢𝗩𝗘 𝗞𝗔𝗥𝗘𝗜𝗡",
        "btn_confirm_no": "❌ 𝗡𝗔𝗛𝗜, 𝗖𝗔𝗡𝗖𝗘𝗟",
        
        "bulk_no_chats": "❌ Bulk Approval use karne ke liye pehle channel ya group add karein.",
        "bulk_select_chat": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗔𝗟 𝗞𝗘 𝗟𝗜𝗬𝗘 𝗖𝗛𝗔𝗧 𝗦𝗘𝗟𝗘𝗖𝗧 𝗞𝗔𝗥𝗘𝗜𝗡",
        
        "bulk_status_title": "⚡ 𝗕𝗨𝗟𝗞 𝗔𝗣𝗣𝗥𝗢𝗩𝗔𝗟 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦: {chat_title}",
        "bulk_status_msg": (
            "📊 Status: {status_icon} {status}\n"
            "📈 Progress: {progress_pct}%\n"
            "📥 Total Pending: {total}\n"
            "✅ Approved: {approved}\n"
            "❌ Failed: {failed}\n"
            "⏭️ Skipped: {skipped}\n"
            "⏳ Remaining: {remaining}\n"
            "🚀 Speed: {speed} req/min"
        ),
        "btn_pause": "⏸️ 𝗣𝗔𝗨𝗦𝗘",
        "btn_resume": "▶️ 𝗥𝗘𝗦𝗨𝗠𝗘",
        "btn_stop": "⛔ 𝗦𝗧𝗢𝗣",
        "btn_refresh": "🔄 𝗥𝗘𝗙𝗥𝗘𝗦𝗛",
        
        "bulk_started": "⚡ Bulk approval start ho gaya hai {chat_title} ke liye.",
        "bulk_paused": "⏸️ Bulk approval pause ho gaya.",
        "bulk_resumed": "▶️ Bulk approval resume ho gaya.",
        "bulk_stopped": "⛔ Bulk approval stop ho gaya.",
        "bulk_completed": "🎉 Bulk approval successfully complete ho gaya!",
        
        "permission_missing_warning": "⚠️ Admin Permission missing hai: <b>Invite Users via Link / Approve Join Requests</b>. Please enable karein.",
        "admin_active": "🟢 𝗔𝗗𝗠𝗜𝗡 𝗔𝗖𝗧𝗜𝗩𝗘",
        "admin_inactive": "🔴 𝗡𝗢𝗧 𝗔𝗗𝗠𝗜𝗡 / RIGHTS CHALE GAYE",
        "active": "🟢 𝗔𝗖𝗧𝗜𝗩𝗘",
        "inactive": "🔴 𝗜𝗡𝗔𝗖𝗧𝗜𝗩𝗘",
        
        "general_settings_title": "⚙️ 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦",
        "btn_change_lang": "🌐 𝗖𝗛𝗔𝗡𝗚𝗘 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘",
    },
    
    "ur": {
        "choose_lang": "𝗖𝗛𝗢𝗢𝗦𝗘 𝗬𝗢𝗨𝗥 𝗟𝗔𝗡𝗚𝗨𝗔𝗚𝗘 / اپنی زبان منتخب کریں",
        "btn_lang_en": "🇬🇧 𝗘𝗡𝗚𝗟𝗜𝗦𝗛",
        "btn_lang_hi": "🇮🇳 𝗛🇮🇳𝗗🇮",
        "btn_lang_hinglish": "🇮🇳 𝗛🇮🇳𝗚𝗟🇮𝗦𝗛",
        "btn_lang_ur": "🇵🇰 𝗨𝗥🇩🇺",
        
        "start_instruction": (
            "بس اس بوٹ کو اپنے چینل یا گروپ میں شامل کریں — نئی شمولیت کی درخواستیں خود بخود قبول ہو جائیں گی۔\n\n"
            "وینم اسٹون نیٹ ورک — t.me/Venom_Stone_Network — اہم چینل۔"
        ),
        
        "btn_add_channel": "➕ چینل میں شامل کریں",
        "btn_add_group": "➕ گروپ میں شامل کریں",
        "btn_bulk_approve": "⚡ پرانی درخواستوں کو ایک ساتھ منظور کریں",
        "btn_my_chats": "📊 میرے چینلز / گروپس",
        "btn_support": "🔗 وینم اسٹون نیٹ ورک میں شامل ہوں",
        
        "fsub_title": "📢 لازمی سبسکرپشن درکار ہے",
        "fsub_msg": "بوٹ استعمال کرنے کے لیے آپ کو درج ذیل چینلز/گروپس میں شامل ہونا یا درخواست بھیجنا ہوگی:",
        "fsub_joined_btn": "🔄 شمولیت چیک کریں",
        "fsub_please_join": "❌ آپ نے ابھی تک تمام مطلوبہ چینلز جوائن نہیں کیے۔ براہ کرم پہلے جوائن کریں۔",
        
        "verify_msg": "ہیلو، آپ نے {chat_title} میں شامل ہونے کی درخواست کی ہے۔\nبراہ کرم ثابت کریں کہ آپ روبوٹ نہیں ہیں۔",
        "verify_btn": "✅ میں روبوٹ نہیں ہوں",
        "verify_success": "✅ آپ کی تصدیق ہو چکی ہے۔ آپ کی درخواست قبول کر لی گئی ہے۔ اب آپ {chat_title} کھول سکتے ہیں۔",
        
        "no_chats": "📊 آپ نے ابھی تک کوئی چینل یا گروپ منسلک نہیں کیا۔ شروع کرنے کے لیے اس بوٹ کو ایڈمن بنا کر شامل کریں۔",
        "chat_list_title": "📊 آپ کے منسلک چیٹس",
        
        "chat_report_title": "🎉 چیٹ کامیابی سے منسلک ہو گیا ہے!",
        "chat_report_details": (
            "📝 نام: {chat_title}\n"
            "🆔 آئی ڈی: <code>{chat_id}</code>\n"
            "🏷️ صارف نام: {username}\n"
            "👤 قسم: {chat_type}\n"
            "👥 ممبران: {member_count}\n"
            "🛡️ ایڈمن حیثیت: {admin_status}\n"
            "⚙️ اختیارات کی حیثیت: {permissions_status}\n"
            "🤖 آٹو منظوری: {auto_approve_status}"
        ),
        
        "chat_settings_title": "⚙️ چیٹ کا انتظام: {chat_title}",
        "btn_auto_approve_on": "🟢 آٹو منظوری: چالو",
        "btn_auto_approve_off": "🔴 آٹو منظوری: بند",
        "btn_bulk_approve_this": "⚡ ایک ساتھ منظور کریں",
        "btn_remove_chat": "❌ ہٹائیں / غیر فعال کریں",
        "btn_back": "⬅️ واپس",
        "btn_home": "🏠 ہوم",
        
        "confirm_remove": "⚠️ کیا آپ واقعی {chat_title} کو ہٹانا چاہتے ہیں؟",
        "btn_confirm_yes": "✅ ہاں، ہٹائیں",
        "btn_confirm_no": "❌ نہیں، منسوخ کریں",
        
        "bulk_no_chats": "❌ بلک منظوری استعمال کرنے کے لیے پہلے ایک چینل/گروپ منسلک کریں۔",
        "bulk_select_chat": "⚡ بلک منظوری کے لیے چیٹ منتخب کریں",
        
        "bulk_status_title": "⚡ بلک منظوری کی پیشرفت: {chat_title}",
        "bulk_status_msg": (
            "📊 حیثیت: {status_icon} {status}\n"
            "📈 پیشرفت: {progress_pct}%\n"
            "📥 کل زیر التواء: {total}\n"
            "✅ منظور شدہ: {approved}\n"
            "❌ ناکام: {failed}\n"
            "⏭️ چھوڑ دیا گیا: {skipped}\n"
            "⏳ باقی: {remaining}\n"
            "🚀 رفتار: {speed} req/min"
        ),
        "btn_pause": "⏸️ روکیں",
        "btn_resume": "▶️ دوبارہ شروع کریں",
        "btn_stop": "⛔ بند کریں",
        "btn_refresh": "🔄 تازہ کریں",
        
        "bulk_started": "⚡ {chat_title} کے لیے بلک منظوری شروع ہو گئی ہے۔",
        "bulk_paused": "⏸️ بلک منظوری روک دی گئی ہے۔",
        "bulk_resumed": "▶️ بلک منظوری دوبارہ شروع کر دی گئی ہے۔",
        "bulk_stopped": "⛔ بلک منظوری بند کر دی گئی ہے۔",
        "bulk_completed": "🎉 بلک منظوری کامیابی سے مکمل ہو گئی!",
        
        "permission_missing_warning": "⚠️ ایڈمن کی اہم اجازت غائب ہے: <b>صارفین کو مدعو کریں / شمولیت کی درخواستیں منظور کریں</b>۔ براہ کرم اسے چالو کریں۔",
        "admin_active": "🟢 ایڈمن چالو",
        "admin_inactive": "🔴 ایڈمن غیر فعال / اختیارات چلے گئے",
        "active": "🟢 فعال",
        "inactive": "🔴 غیر فعال",
        
        "general_settings_title": "⚙️ سیٹنگز",
        "btn_change_lang": "🌐 زبان تبدیل کریں",
    }
}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """
    Retrieves translation for a key, applies formatting, and converts
    the result (Latin characters/numbers/headings) into Unicode bold.
    """
    lang_dict = STRINGS.get(lang, STRINGS["en"])
    text_tmpl = lang_dict.get(key, STRINGS["en"].get(key, ""))
    
    # Format with args if any
    try:
        formatted = text_tmpl.format(**kwargs)
    except Exception:
        formatted = text_tmpl
        
    return to_bold(formatted)
