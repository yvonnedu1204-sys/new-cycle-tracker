import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image, ImageOps
from datetime import datetime, timedelta
import os
import cv2

# ==========================================
# ⚙️ 1. 全局配置与安全锁
# ==========================================

st.set_page_config(
    page_title="My Cycle Pro v4",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 简单密码保护 (沿用 v3) ---
def check_password():
    """返回 True 如果密码正确"""
    if st.secrets.get("PASSWORD"):
        correct_password = st.secrets["PASSWORD"]
    else:
        correct_password = "123" 

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown(
        """
        <style>.stTextInput input {text-align: center;}</style>
        <br><br><h1 style='text-align: center;'>🌸 私密空间</h1>
        """, 
        unsafe_allow_html=True
    )
    password = st.text_input("", type="password", label_visibility="collapsed", placeholder="请输入密码")
    if st.button("解锁进入", type="primary", use_container_width=True):
        if password == correct_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("密码错误")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🎨 2. UI 样式 (P1: 更 Fancy 的 UI)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Nunito', sans-serif;
        background-color: #FFF5F7; 
        color: #333;
    }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; max-width: 500px;}
    
    /* 卡片风格优化 */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 25px;
        box-shadow: 0 10px 30px rgba(255, 133, 161, 0.15); /* 更柔和的深阴影 */
        border: 1px solid #FFF0F5;
    }
    
    /* P1: 更 Fancy 的大圆环 */
    .cycle-circle-container {
        display: flex;
        justify-content: center;
        margin-bottom: 25px;
    }
    .cycle-circle {
        /* 使用更丰富的渐变和多重阴影营造立体感 */
        background: linear-gradient(145deg, #FF9A9E, #FAD0C4);
        border-radius: 50%;
        width: 200px;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        box-shadow: 
            0 15px 30px rgba(255, 107, 139, 0.4),
            inset 0 -5px 15px rgba(0,0,0,0.1);
        position: relative;
        border: 4px solid rgba(255,255,255,0.3);
    }
    
    /* 按钮美化 */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        border: none;
        padding-top: 15px; padding-bottom: 15px;
        transition: all 0.2s;
    }
    /* 次要按钮样式 */
    button[kind="secondary"] {
        background-color: #FFF0F5;
        color: #FF85A1;
        border: 2px solid #FFB6C1;
    }
    
    /* 结果页大字 */
    .metric-value {
        font-size: 3.5rem; font-weight: 800; color: #FF85A1;
        text-align: center; line-height: 1.1;
        text-shadow: 0 2px 10px rgba(255, 133, 161, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 3. 核心算法：真实的图像分析 (P0)
# ==========================================
def analyze_image_real(uploaded_file):
    """
    使用 OpenCV 分析试纸图像。
    原理：将图像转为灰度，寻找水平方向上最暗的区域（代表线条）。
    假设用户横向拍摄，T线在左侧区域，C线在右侧区域。
    """
    # 1. 读取图片
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    # ToDo: 在这里可以加入自动裁剪算法 (findContours)，目前假设用户拍得比较正
    
    # 2. 转灰度并反转 (让深色线条变成高亮数值)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inverted_gray = cv2.bitwise_not(gray) # 黑变白，白变黑。线条现在是高数值区域。

    # 3. 简单的区域划分 (假设 T 在左半边，C 在右半边)
    h, w = inverted_gray.shape
    mid_point = w // 2
    
    # 增加一点边距容错
    margin = int(w * 0.05)
    t_region = inverted_gray[:, margin:mid_point-margin]
    c_region = inverted_gray[:, mid_point+margin:w-margin]

    # 4. 寻找峰值强度
    # 计算每一列的平均强度，然后找出区域内最大的平均强度值
    # 这种方法比只找单个最暗像素更稳定
    t_intensity = np.max(np.mean(t_region, axis=0))
    c_intensity = np.max(np.mean(c_region, axis=0))

    # 5. 防止除以零（如果没有C线，认为无效或强度极低）
    if c_intensity < 30: # 阈值可调
        c_intensity = 255.0 # 防止报错，给一个大基数导致比值很低

    ratio = t_intensity / c_intensity
    
    # 6. 状态判定 (阈值可根据实际试纸品牌调整)
    status = ""
    if ratio >= 1.0:
        status = "峰值 (Peak) ⚡"
    elif ratio >= 0.6:
        status = "强阳 (High)"
    elif ratio >= 0.3:
        status = "弱阳 (Low)"
    else:
        status = "阴性 (Negative)"
        
    return ratio, status, img

# ==========================================
# 💾 4. 数据管理 (沿用 v3)
# ==========================================
class DataManager:
    # ... (保持 v3 的代码不变，为了节省篇幅省略，请直接复制 v3 的 DataManager 类代码到这里) ...
    def __init__(self):
        self.use_cloud = False
        self.csv_file = "ovulation_data.csv" # 改个名字
        try:
            from streamlit_gsheets import GSheetsConnection
            if "connections" in st.secrets and "gsheets" in st.secrets.connections:
                self.conn = st.connection("gsheets", type=GSheetsConnection)
                self.use_cloud = True
        except Exception:
            self.use_cloud = False

    def get_data(self):
        if self.use_cloud:
            try:
                df = self.conn.read(worksheet="Sheet1", ttl=0)
                required_cols = ["date", "type", "value", "status", "note"]
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = ""
                return df
            except Exception as e:
                st.error(f"云端同步失败, 切换回本地: {e}")
                self.use_cloud = False
        
        if os.path.exists(self.csv_file):
            return pd.read_csv(self.csv_file)
        else:
            return pd.DataFrame(columns=["date", "type", "value", "status", "note"])

    def add_record(self, new_record):
        df = self.get_data()
        new_row = pd.DataFrame([new_record])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        if self.use_cloud:
            try:
                self.conn.update(worksheet="Sheet1", data=updated_df)
                return True
            except:
                return False
        else:
            updated_df.to_csv(self.csv_file, index=False)
            return True

db = DataManager()
df_all = db.get_data()

# ==========================================
# 🧠 5. 业务逻辑：周期计算与预测 (P0)
# ==========================================

# P0: 侧边栏增加经期记录功能
with st.sidebar:
    st.header("⚙️ 周期管理")
    # 读取最近一次设置或使用默认
    default_lmp = datetime.now().date() - timedelta(days=14)
    if 'user_lmp' not in st.session_state:
        st.session_state.user_lmp = default_lmp
        
    # 日期选择器
    new_lmp = st.date_input("📅 末次月经开始日 (LMP)", st.session_state.user_lmp)
    if new_lmp != st.session_state.user_lmp:
        st.session_state.user_lmp = new_lmp
        st.rerun() # 刷新页面以更新计算
        
    st.caption("修改日期后，首页状态会自动更新。")

# 计算当前周期状态
today = datetime.now().date()
lmp = st.session_state.user_lmp
cycle_day = (today - lmp).days + 1
# 简易日历预测法 (仅作参考)
ovulation_calendar_est = lmp + timedelta(days=14)

# P0: 基于真实数据的智能预测
suggestion_msg = ""
is_peak_recently = False

if not df_all.empty:
    # 筛选最近 48 小时的试纸记录
    df_lh = df_all[df_all['type'] == 'lh'].copy()
    df_lh['date_dt'] = pd.to_datetime(df_lh['date'])
    recent_lh = df_lh[df_lh['date_dt'] > datetime.now() - timedelta(hours=48)]
    
    # 检查是否有峰值或强阳
    if not recent_lh.empty:
        # 检查是否有 ratio >= 1.0 或 status 包含 Peak/强阳
        peak_records = recent_lh[
            (pd.to_numeric(recent_lh['value'], errors='coerce') >= 0.8) | 
            (recent_lh['status'].str.contains('Peak|强阳', case=False, na=False))
        ]
        if not peak_records.empty:
            is_peak_recently = True
            suggestion_msg = "🔥 **关键时机！** 检测到最近 48h 内有 LH 峰值信号。**强烈建议今明两天安排同房**，受孕几率最高。"

if not suggestion_msg:
    # 如果没有试纸信号，使用日历法兜底
    is_fertile_window = -2 <= (today - ovulation_calendar_est).days <= 2
    if is_fertile_window:
        suggestion_msg = f"🌟 处于日历预计的易孕窗口 (预计排卵: {ovulation_calendar_est.strftime('%m-%d')})。请结合试纸监测。"
    else:
        suggestion_msg = "🌿 当前为非易孕期。保持记录习惯。"

# ==========================================
# 📱 6. 前端页面
# ==========================================

tab1, tab2, tab3 = st.tabs(["🏠 概览", "📸 记录", "📊 趋势"])

# --- Tab 1: 首页 ---
with tab1:
    # P1: 更 Fancy 的圆环 UI
    st.markdown(f"""
    <div class="cycle-circle-container">
        <div class="cycle-circle">
            <div style="font-size: 0.9rem; opacity: 0.9; font-weight:600;">Cycle Day</div>
            <div style="font-size: 4rem; font-weight: 800; line-height: 1; text-shadow: 0 2px 10px rgba(0,0,0,0.1);">{cycle_day}</div>
            <div style="font-size: 0.9rem; margin-top:5px; font-weight:600;">{today.strftime('%b %d')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 智能建议提示条
    if is_peak_recently:
        st.error(suggestion_msg, icon="🔥")
    else:
        st.info(suggestion_msg)

    st.markdown("### 快速操作")
    col1, col2 = st.columns(2)
    with col1:
        # ❤️ 爱心记录按钮
        today_str = datetime.now().strftime('%Y-%m-%d')
        has_sex_today = not df_all.empty and \
                        ((df_all['type'] == 'intimacy') & (df_all['date'].str.contains(today_str))).any()
        
        btn_label = "✅ 今日已爱" if has_sex_today else "❤️ 记录爱爱"
        # 使用 type="secondary" 来改变已记录状态的样式
        if st.button(btn_label, use_container_width=True, type="secondary" if has_sex_today else "primary"):
            if not has_sex_today:
                new_rec = {"date": datetime.now().strftime('%Y-%m-%d %H:%M'), "type": "intimacy", "value": 1.0, "status": "Logged", "note": ""}
                db.add_record(new_rec)
                st.rerun()
            else:
                st.toast("今天已经记录过啦~")

    with col2:
        # P0: 修改按钮功能，点击后在首页展开上传区 (折中替代跳转 Tab)
        show_upload = st.button("📸 记录试纸", use_container_width=True)

    # 首页快速上传区
    if show_upload:
        st.markdown("---")
        st.markdown("##### 快速上传试纸")
        quick_file = st.file_uploader("quick_upload", type=['jpg', 'png'], label_visibility="collapsed")
        if quick_file:
            with st.spinner("正在使用 AI 分析..."):
                # P0: 调用真实分析算法
                ratio, status, img_processed = analyze_image_real(quick_file)
                st.markdown(f"<div class='metric-value'>{ratio:.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:#FF85A1; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)
                
                if st.button("保存结果", key="quick_save"):
                    new_rec = {"date": datetime.now().strftime('%Y-%m-%d %H:%M'), "type": "lh", "value": ratio, "status": status, "note": "Quick Upload"}
                    if db.add_record(new_rec):
                        st.success("已保存！首页状态稍后更新。")
                        st.rerun()


# --- Tab 2: 记录 (完整版) ---
with tab2:
    st.markdown("<h4 style='text-align:center'>上传排卵试纸</h4>", unsafe_allow_html=True)
    st.caption("提示：请横向拍摄，确保T线在左，C线在右，光线充足。")
    uploaded_file = st.file_uploader("", type=['jpg', 'png'], label_visibility="collapsed", key="tab2_upload")

    if uploaded_file:
        st.image(uploaded_file, caption="预览", use_column_width=True)
        
        if st.button("开始精准分析 🪄", type="primary", use_container_width=True):
            with st.spinner("正在进行图像处理和色彩分析..."):
                # P0: 调用真实分析算法
                ratio, status, img_processed = analyze_image_real(uploaded_file)
                
                st.markdown("---")
                # 展示处理后的灰度图，增加专业感 (可选)
                # st.image(img_processed, caption="算法视觉", use_column_width=True, channels="BGR")
                
                st.markdown(f"<div class='metric-value'>{ratio:.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:#FF85A1; font-size: 1.2rem; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)
                
                if ratio >= 0.8:
                    st.warning("检测到高 LH 值！建议每 4 小时复测以捕捉峰值。")

                # 自动保存 (为了体验更流畅，这里改为自动保存)
                new_rec = {"date": datetime.now().strftime('%Y-%m-%d %H:%M'), "type": "lh", "value": ratio, "status": status, "note": "Full Upload"}
                if db.add_record(new_rec):
                    st.toast("✅ 分析结果已自动保存！")


# --- Tab 3: 趋势 (P1/P2 优化) ---
with tab3:
    st.subheader("LH 趋势与记录")
    
    df_fresh = db.get_data()
    
    if not df_fresh.empty:
        df_fresh['date_dt'] = pd.to_datetime(df_fresh['date'])
        df_fresh = df_fresh.sort_values('date_dt')
        
        df_lh = df_fresh[df_fresh['type'] == 'lh'].copy()
        df_sex = df_fresh[df_fresh['type'] == 'intimacy'].copy()
        
        fig = go.Figure()
        
        # LH 曲线
        fig.add_trace(go.Scatter(
            x=df_lh['date_dt'], y=df_lh['value'],
            mode='lines+markers', name='LH浓度',
            line=dict(color='#FF85A1', width=3, shape='spline'),
            fill='tozeroy', fillcolor='rgba(255, 133, 161, 0.2)'
        ))
        
        # 爱心标记
        if not df_sex.empty:
            fig.add_trace(go.Scatter(
                x=df_sex['date_dt'], 
                y=[0.1] * len(df_sex), # 稍微提高一点点
                mode='text', text=['❤️'] * len(df_sex),
                textfont=dict(size=16), name='同房记录', hoverinfo='x+name'
            ))
            
        # P1: 图表优化 (时间格式、缩放)
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(255,255,255,0.5)',
            xaxis=dict(
                showgrid=False,
                tickformat='%m-%d\n%H:%M', # P1: 精确到分钟，换行显示
                fixedrange=False # 允许缩放 (Plotly默认允许，显式声明一下)
            ),
            yaxis=dict(showgrid=True, gridcolor='#eee', range=[0, 2.5], title="T/C 比值"),
            showlegend=False,
            height=350,
            dragmode='pan' # 默认交互模式为平移，也支持捏合缩放
        )
        # 添加峰值辅助线
        fig.add_hline(y=1.0, line_dash="dot", line_color="red", annotation_text="峰值线")
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})
        
        # P2: 数据表优化 (易读性)
        st.write("📝 **最近记录列表**")
        df_display = df_fresh.sort_values('date', ascending=False).copy()
        # 格式化日期
        df_display['时间'] = df_display['date_dt'].dt.strftime('%m-%d %H:%M')
        # 翻译类型
        type_map = {'lh': '🧪 试纸', 'intimacy': '❤️ 同房'}
        df_display['类型'] = df_display['type'].map(type_map).fillna(df_display['type'])
        # 重命名列
        df_display = df_display.rename(columns={'value': '数值/T/C', 'status': '状态'})
        
        st.dataframe(
            df_display[['时间', '类型', '数值/T/C', '状态']],
            hide_index=True,
            use_container_width=True,
            height=300
        )
    else:
        st.info("暂无数据，快去首页记录第一笔吧！")
