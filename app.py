import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import re
import streamlit_antd_components as sac

# --- 페이지 설정 ---
st.set_page_config(page_title="MEL SEARCH", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 💡 사이드바 열기 버튼(>) 공간 확보를 위해 상단 여백(3rem) 유지, 나머지 여백 최소화 */
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
    .stTabs [data-baseweb="tab"] { color: #E2E8F0; font-size: 0.9rem; }
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
        justify-content: space-between !important;
        gap: 5px !important;
    }
    .nav-anchor + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0% !important;
    }
    
    /* 페이지 텍스트 자동 크기 조정 (줄바꿈 방지) */
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

# 헤더 명칭 직관성 향상
st.title("✈️ MEL SEARCH (Cockpit & E/E)")

# --- 세션 상태 ---
if 'doc' not in st.session_state: st.session_state.doc = None
if 'toc_items' not in st.session_state: st.session_state.toc_items = []
if 'sac_tree_data' not in st.session_state: st.session_state.sac_tree_data = []
if 'current_page' not in st.session_state: st.session_state.current_page = 0
if 'chapters' not in st.session_state: st.session_state.chapters = []
if 'rendered_page' not in st.session_state: st.session_state.rendered_page = -1
if 'rendered_img' not in st.session_state: st.session_state.rendered_img = None

def clean(t): return str(t).replace("-", "").replace(" ", "").lower()

# 목차 데이터를 sac.TreeItem 구조로 변환하는 재귀 함수
def build_sac_tree(toc_list):
    tree_items = []
    path = {}
    
    for item in toc_list:
        lvl, title, page = item[0], item[1].strip(), item[2] - 1
        
        # tag 속성에 페이지 번호를 저장하여 클릭 시 식별 가능하게 함
        node = sac.TreeItem(title, tag=str(page))
        
        parent_lvl = lvl - 1
        while parent_lvl > 0 and parent_lvl not in path:
            parent_lvl -= 1
            
        if parent_lvl > 0 and parent_lvl in path:
            # 부모가 있다면 부모의 children에 추가
            if path[parent_lvl].children is None:
                path[parent_lvl].children = []
            path[parent_lvl].children.append(node)
        else:
            # 최상위 레벨인 경우
            tree_items.append(node)
            
        path[lvl] = node
        
    return tree_items

# ==========================================
# 1. 사이드바: 업로드 및 검색 (sac.tree 적용)
# ==========================================
with st.sidebar:
    st.header("📂 파일 업로드")
    uploaded_file = st.file_uploader("PDF 매뉴얼 업로드", type=['pdf'])
    
    if uploaded_file and st.session_state.doc is None:
        st.session_state.doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        toc = st.session_state.doc.get_toc()
        
        # sac 용 트리 데이터 생성
        st.session_state.sac_tree_data = build_sac_tree(toc)
        
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
        t_tree, t1, t2, t3 = st.tabs(["전체 목차", "Entries", "Items", "Oper. Proc."])
        
        # --- 전체 목차 (sac.tree 적용) ---
        with t_tree:
            with st.container(height=500):
                # 반환값이 리스트 형태로 옴 (선택된 항목의 title)
                selected_node = sac.tree(
                    items=st.session_state.sac_tree_data,
                    index=0,
                    align='left',
                    size='sm',
                    icon='journal-text', # 기본 아이콘 설정
                    open_all=False,
                    return_index=False # title 값을 반환받음
                )
                
                # 선택된 노드가 있을 경우, 해당 노드의 tag(페이지 번호)를 찾아 이동
                if selected_node:
                    # 선택된 타이틀을 기반으로 전체 toc에서 페이지 번호를 찾음
                    target_page = next((item['page'] for item in st.session_state.toc_items if item['title'] == selected_node[0]), None)
                    if target_page is not None and st.session_state.current_page != target_page:
                        st.session_state.current_page = target_page
                        st.rerun()

        # --- MEL Entries ---
        with t1:
            sel_ch = st.selectbox("Chapter 선택", ["선택하세요"] + st.session_state.chapters, key="ch_sel")
            s1 = st.text_input("결과 내 검색", key="s1")
            
            if sel_ch != "선택하세요":
                ents = [i for i in st.session_state.toc_items if i['is_ent'] and i['chapter'] == sel_ch and i['title'] != sel_ch]
                if clean(s1):
                    ents = [i for i in ents if clean(s1) in clean(i['title'])]
                
                st.markdown('<div class="list-item-btn">', unsafe_allow_html=True)
                with st.container(height=400):
                    for idx, item in enumerate(ents):
                        if st.button(f"📄 {item['title']}", key=f"btn_ent_{idx}_{item['page']}"):
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
                st.markdown('</div>', unsafe_allow_html=True)

        # --- Operational Proc ---
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
