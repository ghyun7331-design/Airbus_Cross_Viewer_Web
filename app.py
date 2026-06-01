import streamlit as st
import fitz  # PyMuPDF
import re
import base64

st.set_page_config(page_title="✈️ MEL Web Viewer", layout="wide", initial_sidebar_state="collapsed")

if 'toc_items' not in st.session_state:
    st.session_state.toc_items = []
if 'doc_bytes' not in st.session_state:
    st.session_state.doc_bytes = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'chapters' not in st.session_state:
    st.session_state.chapters = ["ALL"]

st.title("✈️ DOCUMENT CROSS-SEARCH (Web Ver.)")

uploaded_file = st.file_uploader("📂 PDF 정비 매뉴얼을 업로드하세요", type="pdf")

if uploaded_file is not None and st.session_state.doc_bytes != uploaded_file.getvalue():
    st.session_state.doc_bytes = uploaded_file.getvalue()
    doc = fitz.open(stream=st.session_state.doc_bytes, filetype="pdf")
    toc = doc.get_toc()
    
    temp_items, path, chapters = [], {}, set()
    for item in toc:
        level, title, page_num = item[0], item[1].strip(), item[2] - 1
        path[level] = title
        keys_to_remove = [k for k in path if k > level]
        for k in keys_to_remove: del path[k]
            
        is_mel_entries = any("mel entries" in path[l].lower() for l in path)
        is_mel_items = any("mel items" in path[l].lower() for l in path)
        is_mel_op = any("mel operational procedures" in path[l].lower() for l in path)
        
        current_chapter = ""
        if is_mel_entries:
            ch_match = re.match(r'^(\d{2})\b', title)
            if ch_match:
                current_chapter = ch_match.group(1)
                chapters.add(current_chapter)
                
        temp_items.append((level, title, page_num, is_mel_entries, is_mel_items, is_mel_op, current_chapter))
        
    st.session_state.toc_items = temp_items
    st.session_state.chapters = ["ALL"] + sorted(list(chapters))
    st.session_state.current_page = 0
    st.success("✅ 파일 로드 완료!")

if st.session_state.toc_items:
    tab1, tab2, tab3 = st.tabs(["🔍 MEL Entries", "🔍 MEL Items", "🔍 Operational Proc."])
    
    def filter_items(search_text, category, selected_chapter="ALL"):
        search_text = search_text.lower().replace("-", "").strip()
        keywords = search_text.split() if search_text else []
        if not keywords and selected_chapter == "ALL": return []
        results = []
        for item in st.session_state.toc_items:
            level, title, page_num, is_ent, is_itm, is_op, ch = item
            title_clean = title.lower().replace("-", "")
            if category == "entries":
                if not is_ent: continue
                if selected_chapter != "ALL" and ch != selected_chapter: continue
            elif category == "items" and not is_itm: continue
            elif category == "op" and not is_op: continue
            if all(kw in title_clean for kw in keywords):
                results.append((title, page_num))
        return results

    with tab1:
        col1, col2 = st.columns([1, 4])
        with col1: ch_select = st.selectbox("Chapter", st.session_state.chapters, key="ch_ent")
        with col2: search_ent = st.text_input("검색어 입력 (띄어쓰기 포함 가능)", key="q_ent")
        results_ent = filter_items(search_ent, "entries", ch_select)
        if results_ent:
            for title, page_num in results_ent:
                if st.button(f"▶ {title}", key=f"ent_{page_num}_{title}"):
                    st.session_state.current_page = page_num
                    st.rerun()

    with tab2:
        search_itm = st.text_input("검색어 입력", key="q_itm")
        results_itm = filter_items(search_itm, "items")
        if results_itm:
            for title, page_num in results_itm:
                if st.button(f"▶ {title}", key=f"itm_{page_num}_{title}"):
                    st.session_state.current_page = page_num
                    st.rerun()

    with tab3:
        search_op = st.text_input("검색어 입력", key="q_op")
        results_op = filter_items(search_op, "op")
        if results_op:
            for title, page_num in results_op:
                if st.button(f"▶ {title}", key=f"op_{page_num}_{title}"):
                    st.session_state.current_page = page_num
                    st.rerun()

    st.divider()
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("◀ 이전 페이지"):
            if st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.rerun()
    with col_nav2:
        st.markdown(f"<h4 style='text-align: center;'>PAGE: {st.session_state.current_page + 1}</h4>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("다음 페이지 ▶"):
            st.session_state.current_page += 1
            st.rerun()

    if st.session_state.doc_bytes:
        doc = fitz.open(stream=st.session_state.doc_bytes, filetype="pdf")
        if 0 <= st.session_state.current_page < len(doc):
            page = doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            st.image(pix.tobytes("png"), use_column_width=True)