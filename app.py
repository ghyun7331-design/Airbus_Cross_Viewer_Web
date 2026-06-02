import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re

# --- 페이지 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 여백 최소화하여 화면 꽉 채우기 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* 탭 상단 고정 (스크롤 시에도 위에 붙어있음) */
    div[data-testid="stTabs"] {
        position: sticky !important;
        top: 0px !important;
        z-index: 9999 !important;
        background-color: #1A2639 !important; 
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }

    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 검색 결과 리스트 디자인 */
    .list-item-btn div[data-testid="stButton"] > button {
        background-color: #101824 !important;
        border: 1px solid #24344D !important;
        color: #E2E8F0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 12px !important;
        width: 100% !important;
        margin-bottom: 2px !important;
    }
    .list-item-btn div[data-testid="stButton"] > button:hover {
        border-color: #00D2FF !important;
        color: #00D2FF !important;
    }

    /* 네비게이션 버튼 1줄 강제 고정 */
    .nav-anchor + div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    .nav-anchor + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0% !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH")

# --- 세션 상태 ---
if 'doc' not in st.session_state: st.session_state.doc = None
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
if 'rendered_page' not in st.session_state: st.session_state.rendered_page = -1
if 'rendered_img' not in st.session_state: st.session_state.rendered_img = None

def clean(t): return str(t).replace("-", "").replace(" ", "").lower()

# ==========================================
# 1. 사이드바: 파일 업로드 및 단순 목차
# ==========================================
with st.sidebar:
    st.header("📂 외부파일 열기")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf'])
    
    if uploaded_file and st.session_state.doc is None:
        st.session_state.doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        toc = st.session_state.doc.get_toc()
        parsed_toc = []
        path = {}
        chapters = []
        cur_ch = ""
        
        for item in toc:
            level, title, p_num = item[0], item[1].strip(), item[2] - 1
            path[level] = title
            for k in list(path.keys()):
                if k > level: del path[k]
            
            is_ent = any("mel entries" in path[l].lower() for l in path)
            is_itm = any("mel items" in path[l].lower() for l in path)
            is_ops = any("mel operational procedures" in path[l].lower() for l in path)
            
            if is_ent and re.match(r'^\d{2}\b', title):
                cur_ch = title
                if cur_ch not in chapters: chapters.append(cur_ch)
            
            parsed_toc.append({
                'level': level, 'title': title, 'page': p_num,
                'is_ent': is_ent, 'is_itm': is_itm, 'is_ops': is_ops, 'chapter': cur_ch
            })
        st.session_state.toc_items = parsed_toc
        st.session_state.chapters = chapters
        st.rerun()

    if st.session_state.doc:
        st.markdown("---")
        st.subheader("📑 목차 (Table of Contents)")
        with st.container(height=500):
            for item in st.session_state.toc_items:
                if item['level'] <= 3:
                    indent = "&nbsp;" * (item['level'] * 4)
                    st.markdown(f"{indent} {item['title']}", unsafe_allow_html=True)

# ==========================================
# 2. 메인 화면: 검색 및 뷰어
# ==========================================
if st.session_state.doc:
    col_l, col_r = st.columns([4, 6])
    
    with col_l:
        t1, t2, t3 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc."])
        
        # --- MEL Entries ---
        with t1:
            st.write("▼ **챕터를 선택하면 하위 항목이 나열됩니다.**")
            
            sel_ch = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel")
            s1 = st.text_input("결과 내 검색", key="s1")
            
            if sel_ch != "선택하세요":
                ents = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == sel_ch and i['title'] != sel_ch]
                
                if clean(s1):
                    ents = [i for i in ents if clean(s1) in clean(i['title'])]
                
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=400):
                    for idx, item in enumerate(ents):
                        # 중복 에러 차단
                        if st.button(f"📄 {item['title']}", key=f"btn_ent_{idx}_{item['page']}"):
                            st.session_state.current_page = item['page']
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # --- MEL Items ---
        with t2:
            s2 = st.text_input("MEL Items 검색", key="s2")
            if clean(s2):
                itms = [i for i in st.session_state.toc_items if i['is_itm'] and clean(s2) in clean(i['title'])]
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=450):
                    for idx, item in enumerate(itms):
                        if st.button(f"📄 {item['title']}", key=f"btn_itm_{idx}_{item['page']}"):
                            st.session_state.current_page = item['page']
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # --- Operational Proc ---
        with t3:
            s3 = st.text_input("Operational Proc. 검색", key="s3")
            if clean(s3):
                ops = [i for i in st.session_state.toc_items if i['is_ops'] and clean(s3) in clean(i['title'])]
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=450):
                    for idx, item in enumerate(ops):
                        if st.button(f"📄 {item['title']}", key=f"btn_ops_{idx}_{item['page']}"):
                            st.session_state.current_page = item['page']
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        # [상단] 네비게이션
        st.markdown('<div class="nav-anchor"></div>', unsafe_allow_html=True)
        nc1_top, nc2_top, nc3_top = st.columns([1, 2, 1])
        with nc1_top:
            if st.button("◀ 이전", key="prev_top", use_container_width=True):
                if st.session_state.current_page > 0: 
                    st.session_state.current_page -= 1
                    st.rerun()
        with nc2_top:
            st.markdown(f"<h4 style='text-align:center; margin-top:5px;'>PAGE: {st.session_state.current_page+1} / {len(st.session_state.doc)}</h4>", unsafe_allow_html=True)
        with nc3_top:
            if st.button("다음 ▶", key="next_top", use_container_width=True):
                if st.session_state.current_page < len(st.session_state.doc)-1: 
                    st.session_state.current_page += 1
                    st.rerun()

        # PDF 이미지 렌더링
        if st.session_state.rendered_page != st.session_state.current_page:
            p = st.session_state.doc.load_page(st.session_state.current_page)
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_img = Image.frombytes("RGB", [pix.width, pix.height
