import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re
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
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; font-size: 0.85rem; padding: 10px 5px !important; }
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
if 'pdf_name' not in st.session_state: st.session_state.pdf_name = "🗂️ 목차" # 기본 탭 이름
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'sac_tree_data' not in st.session_state: st.session_state.sac_tree_data = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
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
# 1. 사이드바: 업로드 및 기존 기능 + 신규 기능
# ==========================================
with st.sidebar:
    st.header("📂 파일 업로드")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf'])
    
    if uploaded_file and st.session_state.doc is None:
        # 파일명을 추출하여 탭 이름으로 저장 (확장자 제거)
        st.session_state.pdf_name = os.path.splitext(uploaded_file.name)[0]
        st.session_state.doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        toc = st.session_state.doc.get_toc()
        st.session_state.sac_tree_data = build_sac_tree(toc)
        
        parsed_toc = []
        path_dict = {}
        chapters = []
        cur_ch = ""
        
        for item in toc:
            level, title, p_num = item[0], item[1].strip(), item[2] - 1
            
            # 동적 콤보박스를 위한 트리 계층(Path) 추적 로직
            path_dict[level] = title
            for k in list(path_dict.keys()):
                if k > level: del path_dict[k]
            current_path = [path_dict[i] for i in sorted(path_dict.keys())]
            
            # 기존 탭(t1, t2, t3)을 위한 레거시 로직 유지
            is_ent = any("mel entries" in p.lower() for p in current_path)
            is_itm = any("mel items" in p.lower() for p in current_path)
            is_ops = any("mel operational procedures" in p.lower() for p in current_path)
            
            if is_ent and re.match(r'^\d{2}\b', title):
                cur_ch = title
                if cur_ch not in chapters: chapters.append(cur_ch)
            
            parsed_toc.append({
                'level': level, 'title': title, 'page': p_num,
                'is_ent': is_ent, 'is_itm': is_itm, 'is_ops': is_ops, 'chapter': cur_ch,
                'path': current_path # 트리 구조 필터링을 위한 속성 추가
            })
        st.session_state.toc_items = parsed_toc
        st.session_state.chapters = chapters
        st.rerun()

    if st.session_state.doc:
        st.markdown("---")
        # 1번 탭 이름은 파일명, 2번 탭은 Search로 변경
        t_tree, t_adv, t1, t2, t3 = st.tabs([f"🗂️ {st.session_state.pdf_name}", "🔍 Search", "Entries", "Items", "Oper."])
        
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

        # --- 2. 콤보 박스 트리 검색 (새로운 Search 기능) ---
        with t_adv:
            st.markdown("##### 🎯 검색 범위 지정")
            
            # 1단계 범위 (대분류)
            level_1_options = ["전체 매뉴얼"] + list(dict.fromkeys([item['path'][0] for item in st.session_state.toc_items if len(item['path']) > 0]))
            scope_1 = st.selectbox("1차 분류", level_1_options, key="scope_1")
            
            selected_path = []
            if scope_1 != "전체 매뉴얼":
                selected_path.append(scope_1)
                
                # 2단계 범위 (중분류 - 1차 분류 선택 시에만 나타남)
                level_2_items = [item['path'][1] for item in st.session_state.toc_items if len(item['path']) > 1 and item['path'][0] == scope_1]
                level_2_options = ["전체"] + list(dict.fromkeys(level_2_items))
                
                if len(level_2_options) > 1:
                    scope_2 = st.selectbox("👉 2차 세부 분류", level_2_options, key="scope_2")
                    if scope_2 != "전체":
                        selected_path.append(scope_2)
                        
                        # 3단계 범위 (소분류 - 2차 분류 선택 시에만 나타남)
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
                    # 선택된 경로(selected_path) 구조와 일치하는지 확인
                    match_scope = True
                    for i, p in enumerate(selected_path):
                        if len(item['path']) <= i or item['path'][i] != p:
                            match_scope = False
                            break
                    
                    # 범위 내에 속하고 키워드가 일치하면 결과 추가
                    if match_scope and clean(adv_keyword) in clean(item['title']):
                        results.append(item)
                
                st.markdown(f"<span style='color:#00D2FF; font-size:0.8rem;'>{len(results)}건의 결과가 발견되었습니다.</span>", unsafe_allow_html=True)
                
                if results:
                    st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                    with st.container(height=300):
                        for idx, res in enumerate(results):
                            if st.button(f"📄 {res['title']}", key=f"adv_{idx}_{res['page']}"):
                                st.session_state.current_page = res['page']
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        # --- 3. 기존 기능: MEL Entries ---
        with t1:
            sel_ch = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel_old")
            s1 = st.text_input("결과 내 검색", key="s1")
            if sel_ch != "선택하세요":
                ents = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == sel_ch and i['title'] != sel_ch]
                if clean(s1): ents = [i for i in ents if clean(s1) in clean(i['title'])]
                
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=400):
                    for idx, item in enumerate(ents):
                        if st.button(f"📄 {item['title']}", key=f"btn_ent_{idx}_{item['page']}"):
                            st.session_state.current_page = item['page']
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. 기존 기능: MEL Items ---
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

        # --- 5. 기존 기능: Operational Proc ---
        with t3:
            s3 = st.text_input("Oper. Proc. 검색", key="s3")
            if clean(s3):
                ops = [i for i in st.session_state.toc_items if i['is_ops'] and clean(s3) in clean(i['title'])]
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=450):
                    for idx, item in enumerate(ops):
                        if st.button(f"📄 {item['title']}", key=f"btn_ops_{idx}_{item['page']}"):
                            st.session_state.current_page = item['page']
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
    st.info("👈 좌측 상단의 화살표(>)를 눌러 사이드바를 열고 PDF 파일을 업로드해 주세요.")
