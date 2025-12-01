import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime, timedelta
import os

# ==========================================
# ⚙️ 1. 全局配置与安全锁
# ==========================================

st.set_page_config(
    page_title="My Cycle Pro",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 简单密码保护 ---
def check_password():
    """返回 True 如果密码正确"""
    if st.secrets.get("PASSWORD"): # 优先从云端密钥获取
        correct_password = st.secrets["PASSWORD"]
    else:
        correct_password = "123" # 本地默认密码 (请修改!)

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # 登录界面
    st.markdown(
        """
        <style>
        .stTextInput input {text-align: center;}
        </style>
        <br><br><br>
        <h1 style='text-align: center;'>🌸 私密空间</h1>
        <p style='text-align: center;'>请输入访问密码</p>
        """, 
        unsafe_allow_html=True
    )
    
    password = st.text_input("", type="password", label_visibility="collapsed")
    
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
# 🎨 2. UI 样式 (复刻设计稿)
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
    .block-container {padding-top: 1.5rem; max-width: 500px;}
    
    /* 卡片风格 */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 25px;
        box-shadow: 0 5px 20px rgba(255, 133, 161, 0.1);
    }
    
    /* 圆环模拟 */
    .cycle-circle {
        background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 100%);
        border-radius: 50%;
        width: 180px;
        height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin: 0 auto 20px auto;
        color: white;
        box-shadow: 0 10px 20px rgba(255, 107, 139, 0.3);
    }
    
    /* 按钮美化 */
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 结果页大字 */
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        color: #FF85A1;
        text-align: center;
        margin: 0;
        line-height: 1.2;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 💾 3. 数据管理 (混合存储：云端 + 本地)
# ==========================================

class DataManager:
    """自动判断是使用 Google Sheets 还是本地 CSV"""
    
    def __init__(self):
        self.use_cloud = False
        self.csv_file = "local_data.csv"
        
        # 检查是否配置了 Google Sheets
        try:
            from streamlit_gsheets import GSheetsConnection
            if "connections" in st.secrets and "gsheets" in st.secrets.connections:
                self.conn = st.connection("gsheets", type=GSheetsConnection)
                self.use_cloud = True
        except Exception:
            self.use_cloud = False

    def get_data(self):
        """读取数据返回 DataFrame"""
        if self.use_cloud:
            try:
                # TTL=0 确保每次读取都是最新的
                df = self.conn.read(worksheet="Sheet1", ttl=0)
                # 确保必需的列存在
                required_cols = ["date", "type", "value", "status", "note"]
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = "" # 补全缺失列
                return df
            except Exception as e:
                st.error(f"云端同步失败: {e}，切换回本地模式")
                self.use_cloud = False
        
        # 本地 CSV 模式
        if os.path.exists(self.csv_file):
            return pd.read_csv(self.csv_file)
        else:
            return pd.DataFrame(columns=["date", "type", "value", "status", "note"])

    def add_record(self, new_record):
        """添加一条新记录"""
        df = self.get_data()
        
        # 转换新记录为 DataFrame
        new_row = pd.DataFrame([new_record])
        
        # 合并
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # 写入
        if self.use_cloud:
            try:
                self.conn.update(worksheet="Sheet1", data=updated_df)
                st.toast("✅ 数据已同步到云端")
                return True
            except:
                st.error("写入云端失败")
                return False
        else:
            updated_df.to_csv(self.csv_file, index=False)
            st.toast("✅ 数据已保存到本地")
            return True

# 初始化数据管理器
db = DataManager()
df_all = db.get_data()

# ==========================================
# 🧠 4. 业务逻辑
# ==========================================

# 设置默认周期参数 (实际使用可以存入数据库，这里简化用Session)
if 'settings' not in st.session_state:
    st.session_state.settings = {"lmp": datetime.now().date() - timedelta(days=14), "cycle": 28}

# 侧边栏设置
with st.sidebar:
    st.header("⚙️ 周期设置")
    new_lmp = st.date_input("末次月经", st.session_state.settings["lmp"])
    new_cycle = st.number_input("周期长度", 21, 40, st.session_state.settings["cycle"])
    st.session_state.settings["lmp"] = new_lmp
    st.session_state.settings["cycle"] = new_cycle

# 计算周期
today = datetime.now().date()
cycle_day = (today - st.session_state.settings["lmp"]).days + 1
next_period = st.session_state.settings["lmp"] + timedelta(days=st.session_state.settings["cycle"])
ovulation_est = next_period - timedelta(days=14)

# ==========================================
# 📱 5. 前端页面
# ==========================================

tab1, tab2, tab3 = st.tabs(["🏠 概览", "📸 记录", "📊 趋势"])

# --- Tab 1: 首页 ---
with tab1:
    # 圆环
    st.markdown(f"""
    <div class="cycle-circle">
        <div style="font-size: 0.9rem; opacity: 0.9;">Cycle Day</div>
        <div style="font-size: 3.5rem; font-weight: 800; line-height: 1;">{cycle_day}</div>
        <div style="font-size: 0.8rem; margin-top:5px;">{today.strftime('%b %d')}</div>
    </div>
    """, unsafe_allow_html=True)

    # 状态
    is_fertile = -2 <= (today - ovulation_est).days <= 2
    if is_fertile:
        st.success(f"🌟 **易孕期窗口** (预计排卵: {ovulation_est.strftime('%m-%d')})")
    else:
        st.info(f"🌿 安全期 / 卵泡期 (预计排卵: {ovulation_est.strftime('%m-%d')})")

    st.markdown("### 快速记录 (Quick Log)")
    col1, col2 = st.columns(2)
    with col1:
        # ❤️ 爱心记录按钮
        # 检查今天是否已记录同房
        today_str = datetime.now().strftime('%Y-%m-%d')
        has_sex_today = not df_all.empty and \
                        ((df_all['type'] == 'intimacy') & (df_all['date'].str.contains(today_str))).any()
        
        btn_label = "✅ 今日已爱" if has_sex_today else "❤️ 记录爱爱"
        if st.button(btn_label, use_container_width=True, type="secondary" if has_sex_today else "primary"):
            if not has_sex_today:
                new_rec = {
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "type": "intimacy",
                    "value": 1.0, # 占位
                    "status": "Logged",
                    "note": ""
                }
                db.add_record(new_rec)
                st.rerun()
            else:
                st.toast("今天已经记录过啦~")

    with col2:
        st.button("💧 记录白带", use_container_width=True)


# --- Tab 2: 拍照 ---
with tab2:
    st.markdown("<h4 style='text-align:center'>上传排卵试纸</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=['jpg', 'png'], label_visibility="collapsed")

    if uploaded_file:
        # 显示图片
        st.image(uploaded_file, caption="已上传", width=200)
        
        # 模拟分析 (实际这里接 OpenCV)
        if st.button("开始分析", type="primary", use_container_width=True):
            with st.spinner("正在计算 T/C 值..."):
                # 模拟逻辑：根据文件名判断，或者随机
                filename = uploaded_file.name.lower()
                lh_ratio = 1.45 if "peak" in filename else np.random.uniform(0.2, 0.8)
                lh_status = "峰值 (Peak)" if lh_ratio >= 1.0 else ("高 (High)" if lh_ratio >= 0.5 else "低 (Low)")
                
                # 结果展示
                st.markdown("---")
                st.markdown(f"<div class='metric-value'>{lh_ratio:.2f}</div>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:#666;'>{lh_status}</p>", unsafe_allow_html=True)
                
                # 自动保存
                new_rec = {
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "type": "lh",
                    "value": lh_ratio,
                    "status": lh_status,
                    "note": "Image Upload"
                }
                db.add_record(new_rec)
                st.success("记录已保存！")

# --- Tab 3: 趋势 ---
with tab3:
    st.subheader("LH 趋势与记录")
    
    # 重新读取数据确保最新
    df_fresh = db.get_data()
    
    if not df_fresh.empty:
        df_fresh['date_dt'] = pd.to_datetime(df_fresh['date'])
        df_fresh = df_fresh.sort_values('date_dt')
        
        # 1. LH 数据
        df_lh = df_fresh[df_fresh['type'] == 'lh']
        # 2. 同房数据
        df_sex = df_fresh[df_fresh['type'] == 'intimacy']
        
        # 绘图
        fig = go.Figure()
        
        # LH 曲线
        fig.add_trace(go.Scatter(
            x=df_lh['date_dt'], y=df_lh['value'],
            mode='lines+markers', name='LH',
            line=dict(color='#FF85A1', width=3, shape='spline'),
            fill='tozeroy', fillcolor='rgba(255, 133, 161, 0.1)'
        ))
        
        # 爱心标记 (在 X 轴上)
        if not df_sex.empty:
            fig.add_trace(go.Scatter(
                x=df_sex['date_dt'], 
                y=[0.05] * len(df_sex), # 固定在底部
                mode='text',
                text=['❤️'] * len(df_sex),
                textfont=dict(size=18),
                name='Intimacy',
                hoverinfo='x'
            ))
            
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#eee', range=[0, 2.0]),
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # 列表
        st.write("📝 **最近记录**")
        st.dataframe(
            df_fresh[['date', 'type', 'value', 'status']].sort_values('date', ascending=False),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("暂无数据，去记录第一笔吧！")