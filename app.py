import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide")

# --- CSS: 전용 리스트박스 및 내비게이션 스타일 정의 ---
st.markdown("""
<style>
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 1. 좌측 사이드바 목차용 버튼 스타일 (텍스트 목록 형태) */
    .sidebar-toc-container div.stButton > button {
        background-color: transparent !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 3px 5px !important;
        font-size: 14px !important;
        color: #E2E8F0 !important;
        width: 100% !important;
        box-shadow: none !important;
    }
    .sidebar-toc-container div.stButton > button:hover {
        color: #00D2FF !important;
        background-color: #2D4263 !important;
    }

    /* 2. 메인 검색창 하부 리스트박스용 버튼 스타일 (테두리가 있는 사각 블록 형태) */
    .listbox-container div.stButton > button {
        background-color: #101824 !important;
        border: 1px solid #24344D !important;
        color: #E2E8F0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 12px !important;
        width: 100% !important;
        border-radius: 4px !important;
        margin-bottom: 2px !important;
    }
    .listbox-container div.stButton > button:hover {
        background-color: #2D4263 !important;
        color: #00D2FF !important;
        border-color: #00D2FF !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH")

# --- 세션 상태 초기화 ---
if 'doc' not in st.session_state: st.session_state.doc = None
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
if 'rendered_page' not in st.session_state: st.session_state.rendered_page = -1
if 'rendered_img' not in st.session_state: st.session_state.rendered_img = None

def clean(text): 
    return str(text).replace("-", "").replace(" ", "").lower()

# ==========================================
# 1. 좌측 패널 (사이드바): 파일 열기 및 대화형 목차
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
            
            # Chapter 전체 이름 추출 (예: "21 Air Conditioning")
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

    # 인터랙티브 목차 기능 구현
    if st.session_state.doc:
        st.markdown("---")
        st.subheader("📑 목차 (클릭 시 이동)")
        st.markdown('<div class="sidebar-toc-container">', unsafe_allow_html=True)
        with st.container(height=500):
            for i, item in enumerate(st.session_state.toc_items):
                if item['level'] <= 3:
                    indent = "　" * (item['level'] - 1)
                    # 각 항목을 버튼화하여 클릭 시 즉시 해당 페이지 디스플레이
                    if st.button(f"{indent}{item['title']}", key=f"side_toc_{i}_{item['page']}"):
                        st.session_state.current_page = item['page']
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. 메인 화면 분할: 검색 탭 및 통합 뷰어
# ==========================================
if st.session_state.doc:
    col_l, col_r = st.columns([4, 6])
    
    with col_l:
        t1, t2, t3 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc."])
        
        # --- 탭 1: MEL Entries ---
        with t1:
            st.write("▼ **챕터를 선택하면 하부 항목이 나열됩니다.**")
            sel_ch = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel")
            s1 = st.text_input("결과 내 검색", key="s1")
            
            if sel_ch != "선택하세요":
                # 선택된 Chapter 전체 문자열과 일치하는 항목으로 범위 엄격 한정
                ch_list = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == sel_ch and i['title'] != sel_ch]
                
                if clean(s1):
                    ch_list = [i for i in ch_list if clean(s1) in clean(i['title'])]
                
                if ch_list:
                    st.markdown('<div class="listbox-container">', unsafe_allow_html=True)
                    with st.container(height=400):
                        for idx, item in enumerate(ch_list):
                            if st.button(f"📄 {item['title']}", key=f"ent_btn_{idx}_{item['page']}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("하위 항목이 없습니다.")

        # --- 탭 2: MEL Items ---
        with t2:
            s2 = st.text_input("MEL Items 검색 (하이픈/띄어쓰기 생략 가능)", key="s2")
            
            # 초기 상태는 빈 화면 유지, 입력 시에만 범위 내에서 리스트업
            if clean(s2):
                res2 = [i for i in st.session_state.toc_items if i['is_itm'] and clean(s2) in clean(i['title'])]
                
                if res2:
                    st.markdown('<div class="listbox-container">', unsafe_allow_html=True)
                    with st.container(height=400):
                        for idx, item in enumerate(res2):
                            if st.button(f"📄 {item['title']}", key=f"itm_btn_{idx}_{item['page']}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("일치하는 검색 결과가 없습니다.")

        # --- 탭 3: Operational Proc. ---
        with t3:
            s3 = st.text_input("Operational Proc. 검색 (하이픈/띄어쓰기 생략 가능)", key="s3")
            
            # 초기 상태 빈 화면 유지, 입력 시에만 범위 내에서 리스트업
            if clean(s3):
                res3 = [i for i in st.session_state.toc_items if i['is_ops'] and clean(s3) in clean(i['title'])]
                
                if res3:
                    st.markdown('<div class="listbox-container">', unsafe_allow_html=True)
                    with st.container(height=400):
                        for idx, item in enumerate(res3):
                            if st.button(f"📄 {item['title']}", key=f"ops_btn_{idx}_{item['page']}"):
                                st.session_state.current_page = item['page']
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("일치하는 검색 결과가 없습니다.")

    # --- 우측 메인 PDF 뷰어 영역 ---
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

        # 도면 이미지 실시간 렌더링 및 캐싱 (입력 창 버벅임 차단)
        if st.session_state.rendered_page != st.session_state.current_page:
            p = st.session_state.doc.load_page(st.session_state.current_page)
            pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
            st.session_state.rendered_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.session_state.rendered_page = st.session_state.current_page
        
        st.image(st.session_state.rendered_img, use_container_width=True)
else:
    st.info("👈 좌측 사이드바에서 PDF 매뉴얼 파일을 업로드해 주세요.")
