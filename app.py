import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="AIRBUS CROSS-SEARCH", page_icon="✈️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
</style>
""", unsafe_allow_html=True)

st.title("✈️ DOCUMENT CROSS-SEARCH & VIEWER (Web Ver.)")

# --- 상태 저장소 초기화 ---
if 'doc' not in st.session_state:
    st.session_state.doc = None
if 'toc_items' not in st.session_state:
    st.session_state.toc_items = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'chapters' not in st.session_state:
    st.session_state.chapters = ["ALL"]
# 💡 속도 향상의 핵심: 렌더링된 이미지 기억하기
if 'rendered_page_num' not in st.session_state:
    st.session_state.rendered_page_num = -1
if 'rendered_image' not in st.session_state:
    st.session_state.rendered_image = None

# ==========================================
# 1. 사이드바 (좌측 패널): 외부 파일 열기
# ==========================================
with st.sidebar:
    st.header("📂 외부파일 열기 (OPEN FILE)")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf', 'docx', 'xlsx'])
    
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
        st.session_state.chapters = ["ALL"] + sorted(list(chapters))
        
    # 사이드바 목차 (요약 버전)
    if st.session_state.doc:
        st.markdown("---")
        st.subheader("📑 목차 (TOC 요약)")
        for item in st.session_state.toc_items:
            if item['level'] <= 2: # 너무 길어지지 않게 상위 레벨만 표시
                indent = "&nbsp;" * (item['level'] * 4)
                st.markdown(f"{indent} {item['title']}")

# ==========================================
# 2. 메인 화면 분할 (검색 탭 / 뷰어)
# ==========================================
if st.session_state.doc:
    col_search, col_viewer = st.columns([4, 6])
    
    with col_search:
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc.", "📁 기타"])
        
        # --- 탭 1: MEL Entries ---
        with tab1:
            sub_col1, sub_col2 = st.columns([1, 3])
            with sub_col1:
                selected_chapter = st.selectbox("Chapter", st.session_state.chapters, key="ch_sel")
            with sub_col2:
                search_text_1 = st.text_input("검색어 입력", key="search1")
                
            filtered_entries = [
                item for item in st.session_state.toc_items 
                if item['is_entries'] 
                and (selected_chapter == "ALL" or item['chapter'] == selected_chapter)
                and (search_text_1.lower() in item['title'].lower())
            ]
            
            # 💡 PC버전처럼 콤보박스(Selectbox)로 변경하여 속도 쾌적화 & 공간 절약
            entry_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_entries]
            selected_entry = st.selectbox("🎯 검색 결과 목록 (클릭하여 이동):", ["대기 중..."] + entry_titles, key="combo1")
            
            if selected_entry != "대기 중...":
                idx = entry_titles.index(selected_entry)
                st.session_state.current_page = filtered_entries[idx]['page']

        # --- 탭 2: MEL Items ---
        with tab2:
            search_text_2 = st.text_input("MEL Items 검색", key="search2")
            filtered_items = [
                item for item in st.session_state.toc_items 
                if item['is_items'] and (search_text_2.lower() in item['title'].lower())
            ]
            
            item_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_items]
            selected_item = st.selectbox("🎯 검색 결과 목록:", ["대기 중..."] + item_titles, key="combo2")
            
            if selected_item != "대기 중...":
                idx = item_titles.index(selected_item)
                st.session_state.current_page = filtered_items[idx]['page']

        # --- 탭 3: Operational Proc ---
        with tab3:
            search_text_3 = st.text_input("Operational Proc. 검색", key="search3")
            filtered_ops = [
                item for item in st.session_state.toc_items 
                if item['is_ops'] and (search_text_3.lower() in item['title'].lower())
            ]
            
            ops_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_ops]
            selected_op = st.selectbox("🎯 검색 결과 목록:", ["대기 중..."] + ops_titles, key="combo3")
            
            if selected_op != "대기 중...":
                idx = ops_titles.index(selected_op)
                st.session_state.current_page = filtered_ops[idx]['page']
                    
        with tab4:
            st.write("추후 외부 문서(Word, Excel 등) 업데이트 공간")

    with col_viewer:
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("◀ 이전 페이지"):
                if st.session_state.current_page > 0:
                    st.session_state.current_page -= 1
        with nav_col2:
            st.markdown(f"<h4 style='text-align: center; color: #00D2FF;'>PAGE: {st.session_state.current_page + 1} / {len(st.session_state.doc)}</h4>", unsafe_allow_html=True)
        with nav_col3:
            if st.button("다음 페이지 ▶"):
                if st.session_state.current_page < len(st.session_state.doc) - 1:
                    st.session_state.current_page += 1

        # 💡 속도 향상의 핵심: 페이지가 안 바뀌었으면 예전 이미지를 그대로 씀 (글자 칠 때마다 버벅임 방지)
        if st.session_state.rendered_page_num != st.session_state.current_page:
            page = st.session_state.doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page_num = st.session_state.current_page
        
        st.image(st.session_state.rendered_image, use_container_width=True)
else:
    st.info("👈 좌측 사이드바의 [Browse files] 버튼을 눌러 PDF 파일을 업로드해 주세요.")
