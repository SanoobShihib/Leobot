class script(object):
    START_TXT = """<b>𝐇𝐞𝐲 {}, 𝐈 𝐀𝐦 <a href=https://t.me/{}>{}</a>, 𝐇𝐚𝐩𝐩𝐲 🖤 𝐓𝐨 𝐇𝐚𝐯𝐞 𝐘𝐨𝐮

𝐇𝐞𝐫𝐞 𝐘𝐨𝐮 𝐂𝐚𝐧 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐌𝐨𝐯𝐢𝐞'𝐬, 𝐉𝐮𝐬𝐭 𝐒𝐞𝐧𝐭 <a href='https://t.me/Leofans_bot'>Movie Name</a> 𝐖𝐢𝐭𝐡 𝐏𝐫𝐨𝐩𝐞𝐫 <a href='https://www.google.com/'>Google</a> 𝐒𝐩𝐞𝐥𝐥𝐢𝐧𝐠..!!

𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐁𝐨𝐭 𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 (𝐎𝐫) 𝐑𝐞𝐩𝐨𝐫𝐭 𝐁𝐮𝐠𝐬..!! 👉 @Sanoobshihab</b>"""
    
    ABOUT_TXT = """✯ 𝙼𝚈 𝙽𝙰𝙼𝙴: {}
✯ 𝙲𝚁𝙴𝙰𝚃𝙾𝚁: <a href=https://t.me/+hl_Pkp8qUOsxMmY1>Sanoob</a>
✯ 𝙻𝙸𝙱𝚁𝙰𝚁𝚈: 𝙿𝚈𝚁𝙾𝙶𝚁𝙰𝙼
✯ 𝙻𝙰𝙽𝙶𝚄𝙰𝙶𝙴: 𝙿𝚈𝚃𝙷𝙾𝙽 𝟹
✯ 𝙳𝙰𝚃𝙰 𝙱𝙰𝚂𝙴: 𝙼𝙾𝙽𝙶𝙾 𝙳𝙱
✯ 𝙱𝙾𝚃 𝚂𝙴𝚁𝚅𝙴𝚁: 𝙷𝙴𝚁𝙾𝙺𝚄
✯ 𝙱𝚄𝙸𝙻𝙳 𝚂𝚃𝙰𝚃𝚄𝚂: Latest [ 𝙱𝙴𝚃𝙰 ]"""

    STATUS_TXT = """★ 𝚃𝙾𝚃𝙰𝙻 𝙵𝙸𝙻𝙴𝚂: <code>{}</code>
★ 𝚃𝙾𝚃𝙰𝙻 𝚄𝚂𝙴𝚁𝚂: <code>{}</code>
★ 𝚃𝙾𝚃𝙰𝙻 𝙲𝙷𝙰𝚃𝚂: <code>{}</code>
★ 𝚄𝚂𝙴𝙳 𝚂𝚃𝙾𝚁𝙰𝙶𝙴: <code>{}</code> 𝙼𝚒𝙱
★ 𝙵𝚁𝙴𝙴 𝚂𝚃𝙾𝚁𝙰𝙶𝙴: <code>{}</code> 𝙼𝚒𝙱"""
    STATUS_TXT2 = """📂 𝖳𝗈𝗍𝖺𝗅 𝖥𝗂𝗅𝖾𝗌     - <code>{}</code>

𝗗𝗕 𝟭
𝖳𝗈𝗍𝖺𝗅 𝖥𝗂𝗅𝖾𝗌         - <code>{}</code>
𝖴𝗌𝖾𝖽 𝖲𝗍𝗈𝗋𝖺𝗀𝖾   - <code>{}</code>MB
𝖥𝗋𝖾𝖾 𝖲𝗍𝗈𝗋𝖺𝗀𝖾    - <code>{}</code>MB

𝗗𝗕 𝟮
𝖳𝗈𝗍𝖺𝗅 𝖥𝗂𝗅𝖾𝗌         - <code>{}</code>
𝖴𝗌𝖾𝖽 𝖲𝗍𝗈𝗋𝖺𝗀𝖾   - <code>{}</code>MB
𝖥𝗋𝖾𝖾 𝖲𝗍𝗈𝗋𝖺𝗀𝖾    - <code>{}</code>MB

𝗗𝗕 𝟯
📦 𝖴𝗌𝖾𝗋𝗌            - <code>{}</code>
🖥️ 𝖢𝗁𝖺𝗍𝗌            - <code>{}</code>
𝖴𝗌𝖾𝖽 𝖲𝗍𝗈𝗋𝖺𝗀𝖾   - <code>{}</code>MB
𝖥𝗋𝖾𝖾 𝖲𝗍𝗈𝗋𝖺𝗀𝖾    - <code>{}</code>MB"""
    HELP_TEXT = """
<b>❗️How to Search Movies Here❓

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

1. Just Send Movie Name and Movie Released Year Correctly.

<blockquote>
Check Google for Correct Movie Spelling and Movie Released Year
</blockquote>

<b>Examples:</b>

<code>Oppam 2016</code>
<code>Baahubali 2015 1080p</code>

<blockquote>
For Getting only 1080p Quality Files
</blockquote>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

<code>Baahubali 2015 Malayalam</code>
<code>Baahubali 2015 Tamil</code>

<blockquote>
For Dubbed Movie Files
</blockquote>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

❗️On Android, Better Use VLC Media Player For Watch Movie's.

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

Cᴏɴᴛᴀᴄᴛ Bᴏᴛ Dᴇᴠᴇʟᴏᴘᴇʀ
(Oʀ) Rᴇᴘᴏʀᴛ Bᴜɢꜱ..!!

👉 @clsupportgroup
</b>
"""

    
    LOG_TEXT_G = """#NewGroup
Group = {}(<code>{}</code>)
Total Members = <code>{}</code>
Added By - {}
"""
    LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Name - {}
"""
    CUSTOM_FILE_CAPTION = """<b>𝐇𝐚𝐢 👋 {mention} 😍
    
{file_name}

╔═══ ᴊᴏɪɴ ᴡɪᴛʜ ᴜs ═══╗ 
➲ <a href='t.me/Clmainchannel'>https://t.me/+Ik14BdOewjQzYjI1</a>
➲ <a href='https://t.me/Clmainchannel'>MAIN CHANNEL</a>
╚═══ ᴊᴏɪɴ ᴡɪᴛʜ ᴜs ═══╝
</b>"""
