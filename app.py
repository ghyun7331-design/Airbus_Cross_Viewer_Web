import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re

# --- 페이지 기본 설정 (다크 테마 느낌) ---
st.set_page_config(page_title="AIRBUS CROSS-SEARCH", page_icon="✈️", layout="wide")

# CSS를 통한 다크 테마 및 레이아웃 미세 조정
st.markdown("""
<style>
    /* 전체 배경색 조정 */
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    /* 탭 디자인 조정 */
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

# ==========================================
# 1. 사이드바 (좌측 패널): 외부 파일 열기 & 목차
# ==========================================
with st.sidebar:
    st.header("📂 외부파일 열기 (OPEN FILE)")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf', 'docx', 'xlsx'])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.pdf'):
            # 업로드된 파일을 PyMuPDF로 읽기
            file_bytes = uploaded_file.read()
            st.session_state.doc = fitz.open(stream=file_bytes, filetype="pdf")
            st.success("✅ 파일 로드 완료!")
            
            # 목차(TOC) 추출 및 파싱 로직
            toc = st.session_state.doc.get_toc()
            parsed_toc = []
            chapters = set()
            
            path = {}
            for item in toc:
                level, title, page_num = item[0], item[1].strip(), item[2] - 1
                path[level] = title
                
                # 하위 레벨 정리
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
            
            # 사이드바 목차(Treeview 대체) 출력
            st.markdown("---")
            st.subheader("📑 목차 (TOC)")
            for item in st.session_state.toc_items:
                # 레벨에 따라 들여쓰기 적용
                indent = "&nbsp;" * (item['level'] * 4)
                # 클릭 시 해당 페이지로 이동하도록 버튼화 (Streamlit 한계상 단순 텍스트로 우선 표기)
                st.markdown(f"{indent} {item['title']} (p.{item['page']+1})")

# ==========================================
# 2. 메인 화면 분할 (검색 탭 / 뷰어)
# ==========================================
if st.session_state.doc:
    # 좌우 4:6 비율로 컬럼 분할
    col_search, col_viewer = st.columns([4, 6])
    
    with col_search:
        # 4개의 탭 생성
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc.", "📁 기타"])
        
        # --- 탭 1: MEL Entries (콤보박스 연동) ---
        with tab1:
            st.write("▼ **챕터 선택 및 검색**")
            sub_col1, sub_col2 = st.columns([1, 3])
            with sub_col1:
                # 1차 콤보박스: 챕터 선택
                selected_chapter = st.selectbox("Chapter", st.session_state.chapters, key="ch_sel")
            with sub_col2:
                search_text_1 = st.text_input("검색어 입력", key="search1")
                
            # 선택된 챕터와 검색어로 필터링
            filtered_entries = [
                item for item in st.session_state.toc_items 
                if item['is_entries'] 
                and (selected_chapter == "ALL" or item['chapter'] == selected_chapter)
                and (search_text_1.lower() in item['title'].lower())
            ]
            
            # 리스트박스 대신 Streamlit의 selectbox나 radio를 활용하여 선택 기능 부여
            if filtered_entries:
                entry_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_entries]
                selected_entry = st.radio("목록에서 선택하세요:", entry_titles, key="radio1")
                # 선택 시 페이지 업데이트
                if selected_entry:
                    idx = entry_titles.index(selected_entry)
                    st.session_state.current_page = filtered_entries[idx]['page']
            else:
                st.info("검색 결과가 없습니다.")

        # --- 탭 2: MEL Items ---
        with tab2:
            search_text_2 = st.text_input("MEL Items 검색", key="search2")
            filtered_items = [
                item for item in st.session_state.toc_items 
                if item['is_items'] and (search_text_2.lower() in item['title'].lower())
            ]
            if filtered_items:
                item_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_items]
                selected_item = st.radio("목록에서 선택하세요:", item_titles, key="radio2")
                if selected_item:
                    idx = item_titles.index(selected_item)
                    st.session_state.current_page = filtered_items[idx]['page']

        # --- 탭 3: Operational Proc ---
        with tab3:
            search_text_3 = st.text_input("Operational Proc. 검색", key="search3")
            filtered_ops = [
                item for item in st.session_state.toc_items 
                if item['is_ops'] and (search_text_3.lower() in item['title'].lower())
            ]
            if filtered_ops:
                ops_titles = [f"{item['title']} (p.{item['page']+1})" for item in filtered_ops]
                selected_op = st.radio("목록에서 선택하세요:", ops_titles, key="radio3")
                if selected_op:
                    idx = ops_titles.index(selected_op)
                    st.session_state.current_page = filtered_ops[idx]['page']
                    
        # --- 탭 4: 기타 기능 (예비) ---
        with tab4:
            st.write("외부 문서(Word, Excel 등) 관련 추가 기능 구현 공간입니다.")

    with col_viewer:
        # 뷰어 네비게이션
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

        # PDF 페이지 렌더링 및 출력
        page = st.session_state.doc.load_page(st.session_state.current_page)
        # 웹 환경에서는 해상도를 높여서 렌더링 (zoom=2)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        st.image(img, use_container_width=True)
else:
    st.info("👈 좌측 사이드바에서 PDF 파일을 업로드해 주세요.")
