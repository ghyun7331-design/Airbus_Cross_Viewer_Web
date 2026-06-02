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
    /* 라디오 버튼 간격 미세 조정 */
    .stRadio > label { margin-bottom: -10px; } 
</style>
""", unsafe_allow_html=True)

# 1. 타이틀 심플하게 변경
st.title("✈️ MEL SEARCH")

# --- 상태 저장소 초기화 ---
if 'doc' not in st.session_state:
    st.session_state.doc = None
if 'toc_items' not in st.session_state:
    st.session_state.toc_items = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'chapters' not in st.session_state:
    st.session_state.chapters = ["ALL"]
# 속도 향상용 캐시
if 'rendered_page_num' not in st.session_state:
    st.session_state.rendered_page_num = -1
if 'rendered_image' not in st.session_state:
    st.session_state.rendered_image = None

# ==========================================
# 좌측 패널 (사이드바): 파일 업로드 전용으로 심플하게 유지
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

# ==========================================
# 메인 화면 분할 (검색 탭 / 뷰어)
# ==========================================
if st.session_state.doc:
    col_search, col_viewer = st.columns([4, 6])
    
    with col_search:
        # 2. 기타 탭을 '기타 (목차)'로 변경
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc.", "📁 기타 (목차)"])
        
        # --- 탭 1: MEL Entries ---
        with tab1:
            sub_col1, sub_col2 = st.columns([1, 2])
            with sub_col1:
                selected_chapter = st.selectbox("Chapter 선택", st.session_state.chapters, key="ch_sel")
            with sub_col2:
                search_text_1 = st.text_input("결과 내 검색", key="search1")
                
            filtered_entries = [
                item for item in st.session_state.toc_items 
                if item['is_entries'] 
                and (selected_chapter == "ALL" or item['chapter'] == selected_chapter)
                and (search_text_1.lower() in item['title'].lower())
            ]
            
            entry_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_entries]
            
            # 3. 특정 챕터 선택 시, 하위 목록이 아래로 펼쳐지는 구조 (PC 뷰어 느낌 구현)
            if selected_chapter != "ALL":
                st.write(f"📂 **Chapter {selected_chapter} 하위 항목**")
                # 리스트 형태로 길게 펼쳐서 보여줌 (스크롤 컨테이너 적용)
                with st.container(height=350):
                    selected_entry = st.radio("목록", ["대기 중..."] + entry_titles, label_visibility="collapsed", key="radio1")
            else:
                # ALL일 때는 리스트가 너무 길어지므로 콤보박스로 유지
                selected_entry = st.selectbox("🎯 전체 검색 결과", ["대기 중..."] + entry_titles, key="combo1")
            
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
                    
        # --- 탭 4: 기타 (목차) ---
        with tab4:
            st.subheader("📑 문서 전체 목차 (Table of Contents)")
            # 2. 사이드바에 있던 목차를 이곳으로 이동, 스크롤 박스로 깔끔하게 처리
            with st.container(height=400):
                for item in st.session_state.toc_items:
                    if item['level'] <= 3: # 너무 깊은 항목은 숨김
                        indent = "&nbsp;" * (item['level'] * 4)
                        # 아이콘 추가로 트리 느낌 강조
                        icon = "📄" if item['level'] == 3 else "📂"
                        st.markdown(f"{indent} {icon} {item['title']} (p.{item['page']+1})")

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

        if st.session_state.rendered_page_num != st.session_state.current_page:
            page = st.session_state.doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page_num = st.session_state.current_page
        
        st.image(st.session_state.rendered_image, use_container_width=True)
else:
    st.info("👈 좌측 상단 [>] 버튼을 눌러 PDF 파일을 업로드해 주세요.")
