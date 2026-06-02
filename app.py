import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re

# --- 페이지 설정 (처음부터 사이드바가 열려있도록 expanded 추가) ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 여백 최소화하여 화면 꽉 채우기 (단, 헤더를 숨기지 않아 메뉴 버튼은 살려둠) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* 탭 상단 고정 */
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

# 화면 전환을 위한 상태 변수
if 't1_step' not in st.session_state: st.session_state.t1_step = 1 
if 't1_selected_ch' not in st.session_state: st.session_state.t1_selected_ch = "선택하세요"

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
            
            # 챕터명 추출 시 PDF에 있는 전체 이름 가져오기
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
        
        # --- MEL Entries (1페이지/2페이지 전환 방식) ---
        with t1:
            if st.session_state.t1_step == 1:
                st.write("▼ **챕터를 선택하면 결과 화면으로 이동합니다.**")
                sel_ch = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel")
                
                if sel_ch != "선택하세요":
                    st.session_state.t1_selected_ch = sel_ch
                    st.session_state.t1_step = 2
                    st.rerun()
                    
            elif st.session_state.t1_step == 2:
                if st.button("◀ 챕터 다시 선택하기 (뒤로 가기)", use_container_width=True):
                    st.session_state.t1_step = 1
                    st.session_state.t1_selected_ch = "선택하세요"
                    st.rerun()
                
                st.markdown(f"**현재 Chapter: {st.session_state.t1_selected_ch}**")
                s1 = st.text_input("결과 내 검색", key="s1")
                
                ents = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == st.session_state.t1_selected_ch and i['title'] != st.session_state.t1_selected_ch]
                
                if clean(s1):
                    ents = [i for i in ents if clean(s1) in clean(i['title'])]
                
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=500):
                    for idx, item in enumerate(ents):
                        # 중복 에러 차단을 위해 idx와 page를 키에 강제 주입
                        if st.button(f"📄 {item['title']}", key=f"btn_ent_2page_{idx}_{item['page']}"):
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
                st
