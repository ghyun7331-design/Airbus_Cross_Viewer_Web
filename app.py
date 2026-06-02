import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re

# --- 페이지 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 챕터 선택용 라디오 버튼(키보드 팝업 방지용) 디자인 */
    div[role="radiogroup"] > label > div:first-child { display: none !important; } 
    div[role="radiogroup"] > label {
        padding: 8px 12px;
        background-color: #101824; 
        border: 1px solid #24344D; 
        border-radius: 4px;
        margin-bottom: 2px !important;
        cursor: pointer;
    }
    div[role="radiogroup"] > label:hover { background-color: #2D4263; }
    
    /* 검색 결과 버튼(리스트박스) 디자인 */
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
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH")

if 'doc' not in st.session_state: st.session_state.doc = None
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
if 'rendered_page' not in st.session_state: st.session_state.rendered_page = -1
if 'rendered_img' not in st.session_state: st.session_state.rendered_img = None

def clean(t): return str(t).replace("-", "").replace(" ", "").lower()

# ==========================================
# 1. 사이드바
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
            
            if is_ent and level == 2 and re.match(r'^\d{2}\b', title):
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
# 2. 메인 화면: 50:50 검색 및 결과 / 뷰어
# ==========================================
if st.session_state.doc:
    col_l, col_r = st.columns([4, 6])
    
    with col_l:
        t1, t2, t3 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc."])
        
        # --- MEL Entries (50:50 분할) ---
        with t1:
            st.markdown("##### 🔍 상단: 검색 조건 (50%)")
            with st.container(height=300):
                sel_ch = st.radio("Chapter 선택", ["선택 대기 중..."] + st.session_state.chapters, label_visibility="collapsed", key="ch_sel_radio")
                st.markdown("---")
                s1 = st.text_input(f"하위 항목 검색 (선택된 Chapter 내)", key="s1")
            
            st.markdown("##### 📄 하단: 검색 결과 (50%)")
            st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
            with st.container(height=300):
                if sel_ch != "선택 대기 중...":
                    ents = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == sel_ch and i['title'] != sel_ch]
                    if clean(s1):
                        ents = [i for i in ents if clean(s1) in clean(i['title'])]
                    
                    if ents:
                        for idx, item in enumerate(ents):
                            if st.button(f"📄 {item['title']}", key=f"btn_ent_{idx}_{item['page']}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    else:
                        st.info("조건에 맞는 결과가 없습니다.")
                else:
                    st.info("상단에서 Chapter를 먼저 선택해 주세요.")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- MEL Items (50:50 분할) ---
        with t2:
            st.markdown("##### 🔍 상단: 검색 조건 (50%)")
            with st.container(height=300):
                s2 = st.text_input("MEL Items 검색 (하이픈/띄어쓰기 생략 가능)", key="s2")
            
            st.markdown("##### 📄 하단: 검색 결과 (50%)")
            st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
            with st.container(height=300):
                if clean(s2):
                    itms = [i for i in st.session_state.toc_items if i['is_itm'] and clean(s2) in clean(i['title'])]
                    if itms:
                        for idx, item in enumerate(itms):
                            if st.button(f"📄 {item['title']}", key=f"btn_itm_{idx}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    else:
                        st.info("일치하는 결과가 없습니다.")
                else:
                    st.info("검색어를 입력하시면 결과가 표시됩니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- Operational Proc (50:50 분할) ---
        with t3:
            st.markdown("##### 🔍 상단: 검색 조건 (50%)")
            with st.container(height=300):
                s3 = st.text_input("Operational Proc. 검색 (하이픈/띄어쓰기 생략 가능)", key="s3")
            
            st.markdown("##### 📄 하단: 검색 결과 (50%)")
            st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
            with st.container(height=300):
                if clean(s3):
                    ops = [i for i in st.session_state.toc_items if i['is_ops'] and clean(s3) in clean(i['title'])]
                    if ops:
                        for idx, item in enumerate(ops):
                            if st.button(f"📄 {item['title']}", key=f"btn_ops_{idx}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    else:
                        st.info("일치하는 결과가 없습니다.")
                else:
                    st.info("검색어를 입력하시면 결과가 표시됩니다.")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 우측 뷰어 ---
    with col_r:
        nc1, nc2, nc3 = st.columns([1, 2, 1])
        with nc1:
            if st.button("◀ 이전", use_container_width=True):
                if st.session_state.current_page > 0: 
                    st.session_state.current_page -= 1
                    st.rerun()
        with nc2:
            st.markdown(f"<h4 style='text-align:center;'>PAGE: {st.session_state.current_page+1} / {len(st.session_state.doc)}</h4>", unsafe_allow_html=True)
        with nc3:
            if st.button("다음 ▶", use_container_width=True):
                if st.session_state.current_page < len(st.session_state.doc)-1: 
                    st.session_state.current_page += 1
                    st.rerun()

        if st.session_state.rendered_page != st.session_state.current_page:
            p = st.session_state.doc.load_page(st.session_state.current_page)
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page = st.session_state.current_page
        st.image(st.session_state.rendered_img, use_container_width=True)
else:
    st.info("👈 사이드바를 열어 PDF 파일을 업로드해 주세요.")
