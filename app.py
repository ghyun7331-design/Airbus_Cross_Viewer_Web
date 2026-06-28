import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import streamlit_antd_components as sac
import os

# --- 페이지 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 사이드바 여백 최소화 */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    
    .stApp { background-color: #1A2639; color: #E2E8F0; }
    
    /* 사이드바 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] { background-color: #24344D; }
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; font-size: 0.9rem; padding: 10px 15px !important; }
    .stTabs [aria-selected="true"] { color: #00D2FF !important; border-bottom: 2px solid #00D2FF !important; }
    
    /* 검색 결과 리스트 디자인 */
    .list-item-btn div[data-testid="stButton"] > button {
        background-color: #101824 !important;
        border: 1px solid #24344D !important;
        color: #E2E8F0 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 6px 10px !important;
        width: 100% !important;
        margin-bottom: 3px !important;
        border-radius: 6px !important;
    }
    .list-item-btn div[data-testid="stButton"] > button:hover {
        border-color: #00D2FF !important;
        color: #00D2FF !important;
        background-color: #1E2D40 !important;
    }

    /* 네비게이션 버튼 1줄 강제 고정 */
    .nav-anchor + div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 5px !important;
    }
    .nav-anchor + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0% !important;
    }
    
    /* 페이지 텍스트 자동 크기 조정 */
    .page-info {
        font-size: clamp(0.7rem, 3.5vw, 1.2rem) !important;
        font-weight: bold;
        text-align: center;
        white-space: nowrap !important;
        overflow: hidden !important;
        margin-top: 5px;
        color: #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

st.title("✈️ MEL SEARCH (Cockpit & E/E)")

# --- 세션 상태 ---
if 'doc' not in st.session_state: st.session_state.doc = None
if 'current_filename' not in st.session_state: st.session_state.current_filename = None
if 'pdf_name' not in st.session_state: st.session_state.pdf_name = "목차"
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'sac_tree_data' not in st.session_state: st.session_state.sac_tree_data = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'rendered_page' not in st.session_state: st.session_state.rendered_page = -1
if 'rendered_img' not in st.session_state: st.session_state.rendered_img = None

def clean(t): return str(t).replace("-", "").replace(" ", "").lower()

# 목차 데이터를 sac.TreeItem 구조로 변환
def build_sac_tree(toc_list):
    tree_items = []
    path = {}
    for item in toc_list:
        lvl, title, page = item[0], item[1].strip(), item[2] - 1
        node = sac.TreeItem(title, tag=str(page))
        parent_lvl = lvl - 1
        while parent_lvl > 0 and parent_lvl not in path: parent_lvl -= 1
        if parent_lvl > 0 and parent_lvl in path:
            if path[parent_lvl].children is None: path[parent_lvl].children = []
            path[parent_lvl].children.append(node)
        else:
            tree_items.append(node)
        path[lvl] = node
    return tree_items

# ==========================================
# 1. 사이드바: 다중 업로드 및 콤보박스 선택
# ==========================================
with st.sidebar:
    st.header("📂 파일 업로드")
    # 다중 파일 업로드 허용 (accept_multiple_files=True)
    uploaded_files = st.file_uploader("PDF 매뉴얼 업로드 (여러 개 선택 가능)", type=['pdf'], accept_multiple_files=True)
    
    if uploaded_files:
        file_dict = {f.name: f for f in uploaded_files}
        
        # 파일이 삭제되어 현재 선택된 파일이 리스트에 없는 경우 초기화
        if st.session_state.current_filename not in file_dict:
            st.session_state.current_filename = None
            
        default_idx = list(file_dict.keys()).index(st.session_state.current_filename) if st.session_state.current_filename else 0
        
        # 콤보박스로 조회할 PDF 선택
        selected_filename = st.selectbox("📖 조회할 매뉴얼 선택", list(file_dict.keys()), index=default_idx)
        
        # 선택된 PDF가 변경되었을 때만 파싱 (성능 최적화)
        if selected_filename != st.session_state.current_filename:
            st.session_state.current_filename = selected_filename
            st.session_state.pdf_name = os.path.splitext(selected_filename)[0]
            
            selected_file = file_dict[selected_filename]
            selected_file.seek(0) # 스트림 포인터 초기화
            st.session_state.doc = fitz.open(stream=selected_file.read(), filetype="pdf")
            
            toc = st.session_state.doc.get_toc()
            st.session_state.sac_tree_data = build_sac_tree(toc)
            
            parsed_toc = []
            path_dict = {}
            
            for item in toc:
                level, title, p_num = item[0], item[1].strip(), item[2] - 1
                
                # 동적 콤보박스를 위한 트리 계층(Path) 추적
                path_dict[level] = title
                for k in list(path_dict.keys()):
                    if k > level: del path_dict[k]
                current_path = [path_dict[i] for i in sorted(path_dict.keys())]
                
                parsed_toc.append({
                    'level': level, 'title': title, 'page': p_num, 'path': current_path
                })
                
            st.session_state.toc_items = parsed_toc
            st.session_state.current_page = 0
            st.session_state.rendered_page = -1
            st.rerun()

    # 파일이 정상적으로 로드된 경우에만 탭(단 2개) 렌더링
    if st.session_state.doc and st.session_state.current_filename:
        st.markdown("---")
        
        # 기존 3개 탭 삭제, 파일명 탭과 Search 탭 2개로 압축
        t_tree, t_adv = st.tabs([f"🗂️ {st.session_state.pdf_name}", "🔍 Search"])
        
        # --- 1. 전체 목차 (Tree View) ---
        with t_tree:
            with st.container(height=550):
                selected_node = sac.tree(
                    items=st.session_state.sac_tree_data,
                    index=0, align='left', size='sm', icon='journal-text', open_all=False, return_index=False
                )
                if selected_node:
                    target_page = next((item['page'] for item in st.session_state.toc_items if item['title'] == selected_node[0]), None)
                    if target_page is not None and st.session_state.current_page != target_page:
                        st.session_state.current_page = target_page
                        st.rerun()

        # --- 2. 콤보 박스 트리 검색 (동적 계층형) ---
        with t_adv:
            st.markdown("##### 🎯 검색 범위 지정")
            
            # 1단계 범위 (대분류)
            level_1_options = ["전체 매뉴얼"] + list(dict.fromkeys([item['path'][0] for item in st.session_state.toc_items if len(item['path']) > 0]))
            scope_1 = st.selectbox("1차 분류", level_1_options, key="scope_1")
            
            selected_path = []
            if scope_1 != "전체 매뉴얼":
                selected_path.append(scope_1)
                
                # 2단계 범위 (중분류)
                level_2_items = [item['path'][1] for item in st.session_state.toc_items if len(item['path']) > 1 and item['path'][0] == scope_1]
                level_2_options = ["전체"] + list(dict.fromkeys(level_2_items))
                
                if len(level_2_options) > 1:
                    scope_2 = st.selectbox("👉 2차 세부 분류", level_2_options, key="scope_2")
                    if scope_2 != "전체":
                        selected_path.append(scope_2)
                        
                        # 3단계 범위 (소분류)
                        level_3_items = [item['path'][2] for item in st.session_state.toc_items if len(item['path']) > 2 and item['path'][0] == scope_1 and item['path'][1] == scope_2]
                        level_3_options = ["전체"] + list(dict.fromkeys(level_3_items))
                        
                        if len(level_3_options) > 1:
                            scope_3 = st.selectbox("👉 3차 세부 항목", level_3_options, key="scope_3")
                            if scope_3 != "전체":
                                selected_path.append(scope_3)
            
            st.markdown("##### 🔑 키워드 입력")
            adv_keyword = st.text_input("검색어", key="adv_search", placeholder="예: APU, FIRE...")
            
            if adv_keyword and clean(adv_keyword):
                results = []
                for item in st.session_state.toc_items:
                    match_scope = True
                    for i, p in enumerate(selected_path):
                        if len(item['path']) <= i or item['path'][i] != p:
                            match_scope = False
                            break
                    
                    if match_scope and clean(adv_keyword) in clean(item['title']):
                        results.append(item)
                
                st.markdown(f"<span style='color:#00D2FF; font-size:0.8rem;'>{len(results)}건의 결과가 발견되었습니다.</span>", unsafe_allow_html=True)
                
                if results:
                    st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                    with st.container(height=350):
                        for idx, res in enumerate(results):
                            if st.button(f"📄 {res['title']}", key=f"adv_{idx}_{res['page']}"):
                                st.session_state.current_page = res['page']
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. 메인 화면: 100% 뷰어 전용
# ==========================================
if st.session_state.doc:
    # [상단] 네비게이션
    st.markdown('<div class="nav-anchor"></div>', unsafe_allow_html=True)
    nc1_top, nc2_top, nc3_top = st.columns([1, 6, 1])
    with nc1_top:
        if st.button("◀", key="prev_top", use_container_width=True):
            if st.session_state.current_page > 0: 
                st.session_state.current_page -= 1
                st.rerun()
    with nc2_top:
        st.markdown(f"<div class='page-info'>PAGE: {st.session_state.current_page+1} / {len(st.session_state.doc)}</div>", unsafe_allow_html=True)
    with nc3_top:
        if st.button("▶", key="next_top", use_container_width=True):
            if st.session_state.current_page < len(st.session_state.doc)-1: 
                st.session_state.current_page += 1
                st.rerun()

    # PDF 이미지 렌더링
    if st.session_state.rendered_page != st.session_state.current_page:
        p = st.session_state.doc.load_page(st.session_state.current_page)
        pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
        st.session_state.rendered_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        st.session_state.rendered_page = st.session_state.current_page
    st.image(st.session_state.rendered_img, use_container_width=True)

    # [하단] 네비게이션
    st.markdown('<div class="nav-anchor"></div>', unsafe_allow_html=True)
    nc1_bot, nc2_bot, nc3_bot = st.columns([1, 6, 1])
    with nc1_bot:
        if st.button("◀", key="prev_bot", use_container_width=True):
            if st.session_state.current_page > 0: 
                st.session_state.current_page -= 1
                st.rerun()
    with nc2_bot:
        st.markdown(f"<div class='page-info'>PAGE: {st.session_state.current_page+1} / {len(st.session_state.doc)}</div>", unsafe_allow_html=True)
    with nc3_bot:
        if st.button("▶", key="next_bot", use_container_width=True):
            if st.session_state.current_page < len(st.session_state.doc)-1: 
                st.session_state.current_page += 1
                st.rerun()
else:
    st.info("👈 좌측 상단의 화살표(>)를 눌러 사이드바를 열고 여러 개의 PDF 파일을 업로드해 보세요.")
