import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 🔥 트리 구조 마법: 일반 버튼을 깔끔한 폴더 목록 텍스트처럼 보이게 만듭니다 */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 2px 10px !important;
        color: #E2E8F0 !important;
        font-family: 'Consolas', monospace;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #2D4263 !important;
        color: #00D2FF !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH")

# --- 상태 저장소 초기화 ---
if 'doc' not in st.session_state:
    st.session_state.doc = None
if 'toc_items' not in st.session_state:
    st.session_state.toc_items = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'rendered_page_num' not in st.session_state:
    st.session_state.rendered_page_num = -1
if 'rendered_image' not in st.session_state:
    st.session_state.rendered_image = None

# ==========================================
# 좌측 패널 (사이드바)
# ==========================================
with st.sidebar:
    st.header("📂 외부파일 열기")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf', 'docx', 'xlsx'])
    
    if uploaded_file is not None and st.session_state.doc is None:
        file_bytes = uploaded_file.read()
        st.session_state.doc = fitz.open(stream=file_bytes, filetype="pdf")
        st.success("✅ 파일 로드 완료!")
        
        toc = st.session_state.doc.get_toc()
        parsed_toc = []
        path = {}
        
        for item in toc:
            level, title, page_num = item[0], item[1].strip(), item[2] - 1
            path[level] = title
            keys_to_remove = [k for k in path if k > level]
            for k in keys_to_remove: del path[k]
            
            is_entries = any("mel entries" in path[l].lower() for l in path)
            is_items = any("mel items" in path[l].lower() for l in path)
            is_ops = any("mel operational procedures" in path[l].lower() for l in path)
            
            ch_val = ""
            if is_entries:
                ch_match = re.match(r'^(\d{2})\b', title)
                if ch_match:
                    ch_val = ch_match.group(1)
                    
            parsed_toc.append({
                'level': level, 'title': title, 'page': page_num,
                'is_entries': is_entries, 'is_items': is_items, 'is_ops': is_ops, 'chapter': ch_val
            })
            
        st.session_state.toc_items = parsed_toc

# ==========================================
# 메인 화면 분할 (검색 탭 / 뷰어)
# ==========================================
if st.session_state.doc:
    col_search, col_viewer = st.columns([4, 6])
    
    with col_search:
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc.", "📁 기타 (목차)"])
        
        # --- 탭 1: MEL Entries (트리 구조 구현) ---
        with tab1:
            search_text_1 = st.text_input("MEL Entries 내에서 검색", key="search1")
            search_term_1 = search_text_1.replace("-", "").strip().lower()
            
            # MEL Entries 범위로만 엄격하게 한정
            entries = [i for i in st.session_state.toc_items if i['is_entries']]
            if search_term_1:
                entries = [i for i in entries if search_term_1 in i['title'].replace("-", "").lower()]
            
            chapters_present = sorted(list(set(i['chapter'] for i in entries)))
            
            st.write("▼ **하위 목록을 보려면 챕터를 클릭하세요 (트리 구조)**")
            with st.container(height=500):
                for ch in chapters_present:
                    ch_items = [i for i in entries if i['chapter'] == ch]
                    if not ch_items: continue
                    
                    ch_label = f"Chapter {ch}" if ch else "기타 항목"
                    # 사진처럼 챕터를 누르면 하위 리스트가 열리는 폴더 구조 생성
                    with st.expander(f"📁 {ch_label} ({len(ch_items)}건)"):
                        for item in ch_items:
                            # 버튼을 텍스트 목록처럼 디자인하여 클릭 즉시 페이지 이동
                            if st.button(f"📄 {item['title']} (p.{item['page']+1})", key=f"btn1_{item['page']}_{item['title']}", use_container_width=True):
                                st.session_state.current_page = item['page']

        # --- 탭 2: MEL Items ---
        with tab2:
            search_text_2 = st.text_input("MEL Items 내에서 검색", key="search2")
            search_term_2 = search_text_2.replace("-", "").strip().lower()
            
            # MEL Items 범위로만 엄격하게 한정
            items = [i for i in st.session_state.toc_items if i['is_items']]
            if search_term_2:
                items = [i for i in items if search_term_2 in i['title'].replace("-", "").lower()]
            
            with st.container(height=500):
                for item in items:
                    if st.button(f"📄 {item['title']} (p.{item['page']+1})", key=f"btn2_{item['page']}_{item['title']}", use_container_width=True):
                        st.session_state.current_page = item['page']

        # --- 탭 3: Operational Proc ---
        with tab3:
            search_text_3 = st.text_input("Operational Proc. 내에서 검색", key="search3")
            search_term_3 = search_text_3.replace("-", "").strip().lower()
            
            # Operational Proc 범위로만 엄격하게 한정
            ops = [i for i in st.session_state.toc_items if i['is_ops']]
            if search_term_3:
                ops = [i for i in ops if search_term_3 in i['title'].replace("-", "").lower()]
            
            with st.container(height=500):
                for item in ops:
                    if st.button(f"📄 {item['title']} (p.{item['page']+1})", key=f"btn3_{item['page']}_{item['title']}", use_container_width=True):
                        st.session_state.current_page = item['page']
                    
        # --- 탭 4: 기타 (목차) ---
        with tab4:
            st.subheader("📑 문서 전체 목차")
            with st.container(height=500):
                for item in st.session_state.toc_items:
                    if item['level'] <= 3:
                        indent = "&nbsp;" * (item['level'] * 4)
                        icon = "📄" if item['level'] == 3 else "📁"
                        st.markdown(f"{indent} {icon} {item['title']} (p.{item['page']+1})")

    with col_viewer:
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            # 페이지 이동 버튼은 'primary' 타입을 주어 버튼 모양 유지
            if st.button("◀ 이전 페이지", type="primary"):
                if st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
        with nav_col2:
            st.markdown(f"<h4 style='text-align: center; color: #00D2FF;'>PAGE: {st.session_state.current_page + 1} / {len(st.session_state.doc)}</h4>", unsafe_allow_html=True)
        with nav_col3:
            if st.button("다음 페이지 ▶", type="primary"):
                if st.session_state.current_page < len(st.session_state.doc) - 1:
                    st.session_state.current_page += 1

        if st.session_state.rendered_page_num != st.session_state.current_page:
            page = st.session_state.doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page_num = st.session_state.current_page
        
        st.image(st.session_state.rendered_image, use_container_width=True)
else:
    st.info("👈 좌측 상단 [>] 버튼을 눌러 PDF 파일을 업로드해 주세요.")
