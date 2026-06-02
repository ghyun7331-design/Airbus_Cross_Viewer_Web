import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 🔥 리스트박스 마법: 라디오 버튼 동그라미 숨기기 & 깔끔한 목록 디자인 */
    div[role="radiogroup"] > label > div:first-child { 
        display: none !important; 
    } 
    div[role="radiogroup"] > label {
        padding: 8px 12px;
        background-color: #101824; 
        border: 1px solid #24344D; 
        border-radius: 4px;
        margin-bottom: 2px !important;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    div[role="radiogroup"] > label:hover { 
        background-color: #2D4263; 
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH")

# --- 상태 저장소 초기화 ---
if 'doc' not in st.session_state: st.session_state.doc = None
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
if 'rendered_page_num' not in st.session_state: st.session_state.rendered_page_num = -1
if 'rendered_image' not in st.session_state: st.session_state.rendered_image = None

# 검색어 정제 함수 (하이픈 및 띄어쓰기 무시)
def clean_text(text):
    return str(text).replace("-", "").replace(" ", "").lower()

# ==========================================
# 좌측 패널 (사이드바): 파일 업로드 & 목차(TOC)
# ==========================================
with st.sidebar:
    st.header("📂 외부파일 열기")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf'])
    
    if uploaded_file is not None and st.session_state.doc is None:
        file_bytes = uploaded_file.read()
        st.session_state.doc = fitz.open(stream=file_bytes, filetype="pdf")
        st.success("✅ 파일 로드 완료!")
        
        toc = st.session_state.doc.get_toc()
        parsed_toc = []
        chapters = set()
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
                    chapters.add(ch_val)
                    
            parsed_toc.append({
                'level': level, 'title': title, 'page': page_num,
                'is_entries': is_entries, 'is_items': is_items, 'is_ops': is_ops, 'chapter': ch_val
            })
            
        st.session_state.toc_items = parsed_toc
        st.session_state.chapters = sorted(list(chapters))
    
    # 문서가 로드되면 사이드바에 목차 출력
    if st.session_state.doc:
        st.markdown("---")
        st.subheader("📑 목차 (Table of Contents)")
        with st.container(height=500):
            for item in st.session_state.toc_items:
                if item['level'] <= 3: # 시각적 피로도를 줄이기 위해 3레벨까지만 표시
                    indent = "&nbsp;" * (item['level'] * 4)
                    icon = "📄" if item['level'] == 3 else "📁"
                    st.markdown(f"{indent} {icon} {item['title']}")

# ==========================================
# 메인 화면 분할 (검색 탭 / 뷰어)
# ==========================================
if st.session_state.doc:
    col_search, col_viewer = st.columns([4, 6])
    
    with col_search:
        tab1, tab2, tab3 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc."])
        
        # --- 탭 1: MEL Entries ---
        with tab1:
            st.write("▼ **챕터를 선택하면 하위 항목이 나열됩니다.**")
            selected_chapter = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel")
            
            if selected_chapter != "선택하세요":
                # 선택한 챕터로 완벽하게 한정
                filtered_entries = [
                    item for item in st.session_state.toc_items 
                    if item['is_entries'] and item['chapter'] == selected_chapter
                ]
                entry_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_entries]
                
                with st.container(height=450):
                    selected_entry = st.radio("목록", ["선택 대기 중..."] + entry_titles, label_visibility="collapsed", key="radio_t1")
                
                if selected_entry != "선택 대기 중...":
                    idx = entry_titles.index(selected_entry)
                    st.session_state.current_page = filtered_entries[idx]['page']

        # --- 탭 2: MEL Items ---
        with tab2:
            search_text_2 = st.text_input("MEL Items 검색 (하이픈 생략 가능)", key="search_t2")
            clean_search_2 = clean_text(search_text_2)
            
            # 검색어가 있을 때만 리스트업 (초기 빈 화면)
            if clean_search_2:
                filtered_items = [
                    item for item in st.session_state.toc_items 
                    if item['is_items'] and clean_search_2 in clean_text(item['title'])
                ]
                
                if filtered_items:
                    item_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_items]
                    with st.container(height=450):
                        selected_item = st.radio("목록", ["선택 대기 중..."] + item_titles, label_visibility="collapsed", key="radio_t2")
                    
                    if selected_item != "선택 대기 중...":
                        idx = item_titles.index(selected_item)
                        st.session_state.current_page = filtered_items[idx]['page']
                else:
                    st.info("일치하는 검색 결과가 없습니다.")

        # --- 탭 3: Operational Proc ---
        with tab3:
            search_text_3 = st.text_input("Operational Proc. 검색 (하이픈 생략 가능)", key="search_t3")
            clean_search_3 = clean_text(search_text_3)
            
            if clean_search_3:
                filtered_ops = [
                    item for item in st.session_state.toc_items 
                    if item['is_ops'] and clean_search_3 in clean_text(item['title'])
                ]
                
                if filtered_ops:
                    ops_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_ops]
                    with st.container(height=450):
                        selected_op = st.radio("목록", ["선택 대기 중..."] + ops_titles, label_visibility="collapsed", key="radio_t3")
                    
                    if selected_op != "선택 대기 중...":
                        idx = ops_titles.index(selected_op)
                        st.session_state.current_page = filtered_ops[idx]['page']
                else:
                    st.info("일치하는 검색 결과가 없습니다.")

    # --- 우측 PDF 뷰어 ---
    with col_viewer:
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ 이전 페이지", use_container_width=True):
                if st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
        with nav_col2:
            st.markdown(f"<h4 style='text-align: center; color: #00D2FF;'>PAGE: {st.session_state.current_page + 1} / {len(st.session_state.doc)}</h4>", unsafe_allow_html=True)
        with nav_col3:
            if st.button("다음 페이지 ▶", use_container_width=True):
                if st.session_state.current_page < len(st.session_state.doc) - 1:
                    st.session_state.current_page += 1

        if st.session_state.rendered_page_num != st.session_state.current_page:
            page = st.session_state.doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page_num = st.session_state.current_page
        
        st.image(st.session_state.rendered_image, use_container_width=True)
else:
    st.info("👈 좌측 상단 [>] 버튼을 눌러 사이드바를 열고 PDF 파일을 업로드해 주세요.")
