import streamlit as st
import os
import random
import time
import json
import base64
import google.generativeai as genai
from audiorecorder import audiorecorder # ⚠️ 核心改变：网页录音组件

# ================= 1. 基础配置 =================
# 云端不需要代理设置

# 👇👇👇 这里的 Key 用于本地测试，上传云端后我们会用 Secrets 管理 👇👇👇
try:
    MY_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    MY_API_KEY = "在这里粘贴您的API_KEY" # 本地运行时用这个

genai.configure(api_key=MY_API_KEY.strip(), transport='rest')

# ⚠️ 核心改变：相对路径，适应云端
MUSIC_ROOT = "music"

AVATAR_LIBRARY = {
    "潮酷猴哥": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f435.svg",
    "呆萌企鹅": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f427.svg",
    "霸气狮王": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f981.svg",
    "国宝熊猫": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f43c.svg",
    "粉嫩小猪": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f437.svg",
    "机灵狐狸": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f98a.svg",
    "可爱兔兔": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f430.svg",
    "慵懒考拉": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f428.svg",
    "高冷猫咪": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f431.svg",
    "憨厚棕熊": "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f43b.svg"
}

# ================= 2. 核心逻辑函数 =================

def get_audio_html(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        # 云端自动播放受浏览器限制，可能需要手动点击
        return f'<audio controls autoplay style="width: 100%;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    except Exception as e:
        return f"播放出错: {e}"

def show_overlay_message(title, sub_text="", color="#FF4B4B", duration=3, icon=""):
    placeholder = st.empty()
    for i in range(duration * 10, 0, -1):
        placeholder.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(255, 255, 255, 0.98); z-index: 9999;
                display: flex; align-items: center; justify-content: center;
                flex-direction: column; text-align: center; animation: fadeIn 0.3s;">
                <div style="font-size: 80px; margin-bottom: 20px;">{icon}</div>
                <h1 style="font-size: 70px; color: {color}; margin: 0; text-shadow: 0px 4px 10px rgba(0,0,0,0.1);">{title}</h1>
                <h2 style="color: #555; font-size: 35px; margin-top: 20px; font-weight: normal;">{sub_text}</h2>
                <div style="margin-top: 30px; width: 200px; height: 5px; background: #eee;">
                    <div style="width: {i* (100/(duration*10))}%; height: 100%; background: {color}; transition: width 0.1s;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        time.sleep(0.1)
    placeholder.empty()

def show_countdown_overlay(seconds=3, title="即将播放..."):
    placeholder = st.empty()
    for i in range(seconds, 0, -1):
        placeholder.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(255, 255, 255, 0.95); z-index: 9999;
                display: flex; align-items: center; justify-content: center;
                flex-direction: column;">
                <div style="font-size: 180px; color: #FF4B4B; font-weight: bold; animation: pulse 0.8s infinite;">{i}</div>
                <h2 style="color: #333; font-size: 40px;">{title}</h2>
            </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
    placeholder.empty()

# ⚠️ 移除了 record_voice_lock_10s (本地版)，改用网页组件 audiorecorder

def ai_judge_json(audio_file_path, correct_answer, player_names):
    """云端 AI 判决"""
    model = genai.GenerativeModel("gemini-2.5-flash") 
    sample = genai.upload_file(audio_file_path)
    player_list_str = "、".join(player_names)
    prompt = f"""任务：判定猜歌。答案：《{correct_answer}》。名单：[{player_list_str}]。
    返回 JSON: {{"detected_text": "...", "winner_name": "...", "is_correct": true/false, "comment": "..."}}"""
    try:
        response = model.generate_content([prompt, sample])
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return {"winner_name": "", "is_correct": False, "comment": "没听清", "detected_text": ""}

def get_song_library(selected_eras):
    playlist = []
    era_map = {"80年代及以前": ["80s", "70s", "60s"], "90年代": ["90s"], "00年代": ["00s"], "10年代及以后": ["10s", "20s"]}
    target_prefixes = []
    for label in selected_eras: target_prefixes.extend(era_map.get(label, []))
    
    # 云端路径检查
    if not os.path.exists(MUSIC_ROOT): return []
    for f in os.listdir(MUSIC_ROOT):
        if f.endswith('.mp3') and any(f.lower().startswith(prefix) for prefix in target_prefixes):
            playlist.append(os.path.join(MUSIC_ROOT, f))
    return playlist

def parse_song_info(filename):
    name_no_ext = os.path.splitext(filename)[0]
    parts = name_no_ext.split('_')
    if len(parts) >= 3: return parts[1], parts[2]
    elif len(parts) == 2: return parts[1], "暂无信息"
    return name_no_ext, "未知"

# ================= 3. 界面样式 =================

st.set_page_config(page_title="家庭猜歌王 V6.1 Cloud", page_icon="🎶", layout="wide")

st.markdown("""<style>
.avatar-box-container { width: 100px; height: 100px; margin: auto; border-radius: 20px; border: 3px solid #e0e0e0; padding: 10px; transition: all 0.3s ease; }
.selected-container { border-color: #FF4B4B !important; background: #fff5f5 !important; }
.score-card { text-align: center; padding: 10px; border: 2px solid #ddd; border-radius: 15px; background: white; margin-bottom: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
.score-num { font-size: 24px; font-weight: bold; color: #FF4B4B; }
.rule-card { padding: 30px; border-radius: 25px; background: #fffbe6; border-left: 10px solid #ffe58f; }

/* 独立超大抢答按钮 CSS */
div[data-testid="stButton"] > button[kind="primary"] {
    height: 100px !important; font-size: 42px !important; font-weight: 900 !important;
    background: linear-gradient(180deg, #FF4B4B 0%, #CC0000 100%) !important;
    border: 5px solid #fff !important; border-radius: 50px !important;
    box-shadow: 0 15px 35px rgba(255, 75, 75, 0.5) !important;
    transition: all 0.2s ease-in-out !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { transform: scale(1.02); }
</style>""", unsafe_allow_html=True)

# ================= 4. 状态逻辑 =================

if 'game_stage' not in st.session_state: st.session_state.game_stage = "HOME"
if 'players' not in st.session_state: st.session_state.players = []
if 'config' not in st.session_state: 
    st.session_state.config = {"mode": "抢答赛", "rules": "答错扣分", "rounds": 10, "eras": ["90年代"], "referee_mode": "手动裁判"}

if 'playlist' not in st.session_state: st.session_state.playlist = []
if 'round_idx' not in st.session_state: st.session_state.round_idx = 0
if 'round_finished' not in st.session_state: st.session_state.round_finished = False
if 'temp_avatar_key' not in st.session_state: st.session_state.temp_avatar_key = list(AVATAR_LIBRARY.keys())[0]

# 手动模式子状态
if 'manual_step' not in st.session_state: st.session_state.manual_step = "IDLE" 
if 'current_guesser' not in st.session_state: st.session_state.current_guesser = None

# --- 阶段一：主页 ---
if st.session_state.game_stage == "HOME":
    st.title("🎶 家庭猜歌王 - Web版")
    st.caption("提示：此版本支持手机直接访问")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.config["referee_mode"] = st.radio("裁判模式", ["手动裁判", "AI裁判"], 
                index=0 if st.session_state.config["referee_mode"]=="手动裁判" else 1, horizontal=True)
            st.session_state.config["rules"] = st.radio("计分规则", ["答错扣分", "答错不扣分"], 
                index=0 if st.session_state.config["rules"]=="答错扣分" else 1, horizontal=True)
        with c2:
            st.session_state.config["rounds"] = st.select_slider("比赛轮数", [3, 5, 10, 15, 20], value=st.session_state.config["rounds"])
            st.session_state.config["eras"] = st.multiselect("歌曲年代", ["80年代及以前", "90年代", "00年代", "10年代及以后"], default=st.session_state.config["eras"])

    with st.container(border=True):
        st.subheader("🎭 选手入场")
        cl, cr = st.columns([1, 3])
        with cl:
            name = st.text_input("新增昵称", key="input_nm")
            st.markdown(f'<div style="text-align:center"><img src="{AVATAR_LIBRARY[st.session_state.temp_avatar_key]}" class="avatar-box-container selected-container"></div>', unsafe_allow_html=True)
            if st.button("🚀 加入比赛", use_container_width=True, key="join_btn"):
                if name and not any(p['name']==name for p in st.session_state.players):
                    st.session_state.players.append({"name": name, "avatar": AVATAR_LIBRARY[st.session_state.temp_avatar_key], "score": 0})
                    st.rerun()
        with cr:
            st.write("点击更换形象：")
            cols = st.columns(5)
            for i, (k, v) in enumerate(AVATAR_LIBRARY.items()):
                with cols[i%5]:
                    st.markdown(f'<div class="avatar-box-container {"selected-container" if st.session_state.temp_avatar_key == k else ""}"><img src="{v}" style="width:100%;"></div>', unsafe_allow_html=True)
                    if st.button(k, key=f"ab_{i}", use_container_width=True): 
                        st.session_state.temp_avatar_key = k; st.rerun()

    if st.session_state.players:
        st.write("### 🎮 参赛阵容 (已保存)")
        pc = st.columns(6)
        for i, p in enumerate(st.session_state.players):
            with pc[i]:
                st.markdown(f'<div class="score-card"><img src="{p["avatar"]}" style="width:40px;"><div>{p["name"]}</div></div>', unsafe_allow_html=True)
                if st.button("退出", key=f"q_{i}"): st.session_state.players.pop(i); st.rerun()
        if st.button("🏁 配置完成，去开赛", use_container_width=True, type="primary"): 
            st.session_state.game_stage = "RULES"; st.rerun()

# --- 阶段二：规则页 ---
elif st.session_state.game_stage == "RULES":
    st.title("📋 赛前规则确认")
    rule_txt = "答错扣 15 分" if st.session_state.config["rules"] == "答错扣分" else "答错不扣分"
    st.markdown(f"""<div class="rule-card"><h2>📢 模式：{st.session_state.config["referee_mode"]}</h2><ul><li>🎙️ 判定：{st.session_state.config["referee_mode"]}进行计分。</li><li>💰 奖惩：答对 +10，{rule_txt}。</li><li>⚔️ 平局：自动进入加时赛。</li></ul></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("⬅️ 返回", use_container_width=True, key="rule_back"): 
            st.session_state.game_stage = "HOME"; st.rerun()
    with c2:
        if st.button("🎮 即刻开赛！", use_container_width=True, type="primary"):
            songs = get_song_library(st.session_state.config['eras'])
            if not songs: st.error("⚠️ 没歌了！请检查 music 文件夹")
            else:
                random.shuffle(songs); st.session_state.playlist = songs[:st.session_state.config['rounds']]
                st.session_state.round_idx = 0; st.session_state.round_finished = False; 
                for p in st.session_state.players: p['score'] = 0
                show_countdown_overlay(3); st.session_state.game_stage = "PLAYING"; st.rerun()

# --- 阶段三：比赛现场 ---
elif st.session_state.game_stage == "PLAYING":
    col_t, col_h = st.columns([4, 1])
    with col_t: st.title(f"🎵 激战中 ({st.session_state.config['referee_mode']})")
    with col_h: 
        if st.button("🏠 返回主页", key="back_home"): st.session_state.game_stage = "HOME"; st.rerun()

    scols = st.columns(len(st.session_state.players))
    scores = [p['score'] for p in st.session_state.players]
    high_val = max(scores) if scores else 0
    for i, p in enumerate(st.session_state.players):
        with scols[i]:
            style = "border: 3px solid #FF4B4B;" if p['score'] == high_val and (high_val != 0 or st.session_state.round_idx > 0) else ""
            st.markdown(f'<div class="score-card" style="{style}"><img src="{p["avatar"]}" style="width:40px;"><div>{p["name"]}</div><div class="score-num">{p["score"]}</div></div>', unsafe_allow_html=True)

    if st.session_state.round_idx < len(st.session_state.playlist):
        song_path = st.session_state.playlist[st.session_state.round_idx]
        true_name, true_singer = parse_song_info(os.path.basename(song_path))
        st.subheader(f"第 {st.session_state.round_idx + 1} 轮 / 共 {len(st.session_state.playlist)} 轮")
        
        if not st.session_state.round_finished:
            audio_area = st.empty()
            if st.session_state.manual_step == "IDLE":
                audio_area.markdown(get_audio_html(song_path), unsafe_allow_html=True)
            
            # --- AI 裁判逻辑 (云端修改版) ---
            if st.session_state.config['referee_mode'] == "AI裁判":
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("🎙️ 点击下方录音（点一下开始，说完点停止）：")
                
                # ⚠️ 使用网页录音组件
                audio = audiorecorder("🎤 开始抢答", "⏹️ 结束录音")
                
                if len(audio) > 0: # 检测到录音
                    audio.export("guess.wav", format="wav") # 保存
                    audio_area.empty() # 停止音乐
                    
                    with st.spinner("AI 云端分析中..."):
                        res = ai_judge_json("guess.wav", true_name, [p['name'] for p in st.session_state.players])
                    
                    if res['winner_name'] and res['is_correct']:
                        for p in st.session_state.players:
                            if p['name'] == res['winner_name']: p['score'] += 10
                        show_overlay_message(f"🎉 {res['winner_name']} 答对", f"识别：{res['detected_text']}", color="#28a745", icon="✅")
                        st.session_state.round_finished = True; st.rerun()
                    else:
                        if st.session_state.config['rules'] == "答错扣分" and res['winner_name']:
                            for p in st.session_state.players:
                                if p['name'] == res['winner_name']: p['score'] -= 15
                        show_overlay_message("❌ 判定错误", f"识别：{res['detected_text']}", color="#FF4B4B", icon="🚫")
                        # ⚠️ 注意：云端版这里不自动 rerun，否则录音组件会无限循环提交
                        # 用户需要手动点击“重试”或“跳过”

            # --- 手动裁判逻辑 (保持 V6.1 逻辑) ---
            else:
                if st.session_state.manual_step == "IDLE":
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🎤 抢答开始", type="primary", use_container_width=True):
                        st.session_state.manual_step = "SELECT_PLAYER"; st.rerun()
                
                elif st.session_state.manual_step == "SELECT_PLAYER":
                    audio_area.empty()
                    st.warning("⏱️ 请确认抢答者身份！")
                    sc1, sc2 = st.columns([4, 1])
                    with sc2: countdown_holder = st.empty()
                    with sc1:
                        cols = st.columns(len(st.session_state.players))
                        for i, p in enumerate(st.session_state.players):
                            with cols[i]:
                                st.image(p['avatar'], width=60)
                                if st.button(p['name'], key=f"sel_{i}", use_container_width=True):
                                    st.session_state.current_guesser = p
                                    st.session_state.manual_step = "JUDGE"; st.rerun()
                    for s in range(50, 0, -1):
                        countdown_holder.markdown(f"<h1 style='color:red; text-align:right;'>{s/10:.1f}</h1>", unsafe_allow_html=True)
                        time.sleep(0.1)
                        if st.session_state.manual_step != "SELECT_PLAYER": break
                    else: st.session_state.manual_step = "IDLE"; st.rerun()

                elif st.session_state.manual_step == "JUDGE":
                    p = st.session_state.current_guesser
                    with st.container(border=True):
                        st.markdown(f"### 📢 正在审判：{p['name']}")
                        with st.expander("👁️ 裁判点此查看正确答案", expanded=False):
                            st.write(f"正确答案是：**《{true_name}》**")
                            st.write(f"演唱歌手：**{true_singer}**")
                    st.info("请在20秒内决定是否给分：")
                    countdown_bar = st.progress(1.0)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 判定正确 (+10)", use_container_width=True):
                            p['score'] += 10
                            show_overlay_message(f"🎉 {p['name']} 正确！", f"答案是《{true_name}》", color="#28a745", icon="✅")
                            st.session_state.manual_step = "IDLE"; st.session_state.round_finished = True; st.rerun()
                    with c2:
                        if st.button("❌ 判定错误 (-15)", use_container_width=True):
                            if st.session_state.config['rules'] == "答错扣分": p['score'] -= 15
                            show_overlay_message(f"🚫 {p['name']} 错误！", f"正确答案是《{true_name}》", color="#FF4B4B", icon="🚫")
                            st.session_state.manual_step = "IDLE"; st.rerun()
                    for s in range(200, 0, -1):
                        countdown_bar.progress(s/200); time.sleep(0.1)
                        if st.session_state.manual_step != "JUDGE": break
                    else:
                        if st.session_state.config['rules'] == "答错扣分": p['score'] -= 15
                        show_overlay_message("⏰ 超时扣分", f"由于没有及时操作", color="#FF4B4B", icon="⌛"); st.session_state.manual_step = "IDLE"; st.rerun()

            # 通用功能
            st.markdown("<br>", unsafe_allow_html=True)
            c2, c3, c4 = st.columns(3)
            with c2:
                if st.button("💡 提示歌手", use_container_width=True): show_overlay_message(f"歌手：{true_singer}", "加油！", color="#17a2b8", duration=2, icon="🎤")
            with c3:
                if st.button("🔄 再听一遍", use_container_width=True): st.rerun()
            with c4:
                if st.button("⏭️ 跳过", use_container_width=True): st.session_state.round_finished = True; st.rerun()
        else:
            st.success(f"本轮答案：《{true_name}》 (歌手：{true_singer})")
            if st.button("👉 下一题", type="primary", use_container_width=True):
                show_countdown_overlay(3); st.session_state.round_idx += 1; st.session_state.round_finished = False; st.rerun()
    else:
        high_score = max([p['score'] for p in st.session_state.players])
        winners = [p for p in st.session_state.players if p['score'] == high_score]
        if len(winners) > 1:
            st.warning(f"⚖️ 平局！最高分 ({high_score}) 并列人数：{len(winners)}。")
            if st.button("🔥 开启决胜局", type="primary", use_container_width=True):
                all_s = get_song_library(st.session_state.config['eras'])
                rem = [s for s in all_s if s not in st.session_state.playlist]
                if rem:
                    st.session_state.playlist.append(random.choice(rem)); st.session_state.round_finished = False
                    show_countdown_overlay(3, title="⚔️ 巅峰对决！"); st.rerun()
                else: st.error("没歌了！")
        else:
            st.balloons(); win = winners[0]
            st.markdown(f"<div style='text-align:center; padding:40px; background:#fffbe6; border-radius:20px;'><h1>👑 冠军：{win['name']}</h1><h2>总分：{win['score']}</h2><img src='{win['avatar']}' style='width:120px;'></div>", unsafe_allow_html=True)
            if st.button("🏠 返回主页 (保存配置)", use_container_width=True, key="home_final"): 
                st.session_state.game_stage = "HOME"; st.rerun()