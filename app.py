import io
import json
import os
from collections import Counter
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM: База и Структура", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v10.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "known_articles" not in data:
          data["known_articles"] = []
        return data
    except:
      pass
  return {
      "categories": {},
      "breadcrumbs_tree": [],
      "global_glossary": {},
      "known_articles": [],
      "base_columns": [
          "артикул",
          "код",
          "название",
          "id",
          "url",
          "скрыта",
          "бренд",
          "описание",
          "картинок",
          "документ",
          "сертификат",
          "breadcrumbs",
      ],
  }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


db = load_db()

st.title("🧠 MDM-Система: Управление базой и структурой")

tab_import, tab_structure, tab_glossary, tab_required = st.tabs([
    "📥 Загрузка файлов",
    "📂 Структура и категории",
    "📚 Глоссарий и значения",
    "⭐ Обязательные поля",
])

# ВКЛАДКА 1: ЗАГРУЗКА И БД
with tab_import:
  st.subheader("💾 Управление базой данных (.json)")
  db_col1, db_col2 = st.columns(2)

  with db_col1:
    db_json_bytes = json.dumps(db, ensure_ascii=False, indent=4).encode(
        "utf-8"
    )
    st.download_button(
        label="📥 Скачать базу данных (.json)",
        data=db_json_bytes,
        file_name="mdm_database_backup.json",
        mime="application/json",
        use_container_width=True,
    )

  with db_col2:
    uploaded_db_file = st.file_uploader(
        "📤 Загрузить готовую базу данных (.json)",
        type=["json"],
        key="up_json_db",
    )
    if uploaded_db_file is not None:
      try:
        imported_data = json.load(uploaded_db_file)
        if isinstance(imported_data, dict) and "categories" in imported_data:
          db.clear()
          db.update(imported_data)
          if "known_articles" not in db:
            db["known_articles"] = []
          save_db(db)
          st.success("✅ База данных успешно восстановлена!")
          st.rerun()
        else:
          st.error("Неверный формат JSON.")
      except Exception as e:
        st.error(f"Ошибка: {e}")

  st.markdown("---")
  st.subheader("📥 Импорт файлов выгрузки сайта")
  uploaded_file = st.file_uploader(
      "Загрузите Excel или CSV выгрузку", type=["xlsx", "xls", "csv"], key="up_main"
  )

  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        raw_bytes = uploaded_file.read()
        text_data = None
        for enc in ["utf-8-sig", "cp1251", "utf-8", "latin1"]:
          try:
            text_data = raw_bytes.decode(enc)
            break
          except UnicodeDecodeError:
            continue
        df = pd.read_csv(
            io.StringIO(text_data),
            sep=None,
            engine="python",
            encoding_errors="replace",
            on_bad_lines="skip",
        )
      else:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
      st.error(f"Ошибка чтения файла: {e}")
      st.stop()

    art_col = None
    for c in df.columns:
      if str(c).lower() in ["артикул", "artikul", "article", "sku", "код"]:
        art_col = c
        break

    known_set = set(str(x) for x in db.get("known_articles", []))
    if art_col and art_col in df.columns and known_set:
      initial_len = len(df)
      df = df[
          ~df[art_col]
          .astype(str)
          .str.strip()
          .isin(known_set)
          | df[art_col].isna()
      ]
      skipped = initial_len - len(df)
      if skipped > 0:
        st.warning(
            f"⚠️ Пропущено дублирующихся строк (артикулы уже в базе): `{skipped}`"
        )

    st.success(f"Строк к обработке: {len(df)}")

    if len(df) > 0:
      cat_col = None
      for c in df.columns:
        if (
            "breadcrumb" in c.lower()
            or "крошк" in c.lower()
            or "раздел" in c.lower()
        ):
          cat_col = c
          break

      full_bc_chains = []
      if cat_col and cat_col in df.columns:
        for cell in df[cat_col].dropna().astype(str).unique().tolist():
          for branch in cell.split(";"):
            parts = [p.strip() for p in branch.split(">") if p.strip()]
            if parts:
              chain = " > ".join(parts)
              if chain not in full_bc_chains:
                full_bc_chains.append(chain)
              curr = []
              for p in parts:
                curr.append(p)
                p_str = " > ".join(curr)
                if p_str not in db["categories"]:
                  db["categories"][p_str] = {"required_attributes": []}

      if st.button("🚀 Обработать файл и обновить базу данных", type="primary"):
        for chain in full_bc_chains:
          if chain not in db["breadcrumbs_tree"]:
            db["breadcrumbs_tree"].append(chain)

        new_arts = 0
        if art_col and art_col in df.columns:
          for art in df[art_col].dropna().astype(str).str.strip().tolist():
            if art and art not in db["known_articles"]:
              db["known_articles"].append(art)
              new_arts += 1

        added_attrs = 0
        for col in df.columns:
          if not any(kw in str(col).lower() for kw in db["base_columns"]):
            vals = [
                v.strip()
                for v in df[col].dropna().astype(str).tolist()
                if v.strip()
            ]
            if vals:
              if col not in db["global_glossary"]:
                db["global_glossary"][col] = {
                    "values": {},
                    "is_numeric": False,
                    "total_filled": 0,
                }
              db["global_glossary"][col]["total_filled"] += len(vals)
              vc = Counter(vals)
              all_num = True
              for v in vc.keys():
                try:
                  float(v.replace(",", ".").replace(" ", "").replace("%", ""))
                except:
                  all_num = False
                  break
              if all_num:
                db["global_glossary"][col]["is_numeric"] = True
              else:
                for v, cnt in vc.items():
                  db["global_glossary"][col]["values"][v] = (
                      db["global_glossary"][col]["values"].get(v, 0) + cnt
                  )
              added_attrs += 1

        save_db(db)
        st.success(
            f"✅ Готово! Новых артикулов: {new_arts}, характеристик:"
            f" {added_attrs}"
        )

# ВКЛАДКА 2: СТРУКТУРА
with tab_structure:
  st.subheader("📂 Иерархическое дерево структуры каталога")
  if not db["categories"]:
    st.info("Сначала загрузите файлы.")
  else:

    def build_tree(chains):
      tree = {}
      for ch in chains:
        parts = [p.strip() for p in ch.split(">") if p.strip()]
        cur = tree
        for p in parts:
          if p not in cur:
            cur[p] = {}
          cur = cur[p]
      return tree

    def render_tree(sub):
      for name, s in sorted(sub.items()):
        if len(s) > 0:
          with st.expander(f"📁 {name}", expanded=False):
            render_tree(s)
        else:
          st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 `{name}`")

    render_tree(build_tree(db["breadcrumbs_tree"]))

# ВКЛАДКА 3: ГЛОССАРИЙ
with tab_glossary:
  st.subheader("📚 Управление глоссарием")
  glossary = db["global_glossary"]
  if not glossary:
    st.info("Глоссарий пуст.")
  else:
    cl, cr = st.columns([4, 6], gap="large")
    with cl:
      if st.button("🗑️ Удалить выбранные заголовки", type="primary"):
        to_del = [
            a
            for a in glossary.keys()
            if st.session_state.get(f"chk_attr_{a}", False)
        ]
        for a in to_del:
          glossary.pop(a, None)
        save_db(db)
        st.success(f"Удалено: {len(to_del)}")
        st.rerun()
      st.markdown("---")
      all_a = list(glossary.keys())
      if (
          "active_attr" not in st.session_state
          or st.session_state.active_attr not in glossary
      ):
        st.session_state.active_attr = all_a[0] if all_a else None
      for a in all_a:
        tot = glossary[a].get("total_filled", 0)
        badge = f"({tot} зап.)"
        cc, cb = st.columns([1, 10])
        with cc:
          st.checkbox("", key=f"chk_attr_{a}", label_visibility="collapsed")
        with cb:
          if st.button(
              f"{a} {badge}",
              key=f"btn_attr_{a}",
              use_container_width=True,
              type=(
                  "primary" if st.session_state.active_attr == a else "secondary"
              ),
          ):
            st.session_state.active_attr = a
            st.rerun()
    with cr:
      act = st.session_state.get("active_attr")
      if act and act in glossary:
        st.markdown(f"### ⚙️ {act}")
        if not glossary[act].get("is_numeric", False):
          vals = glossary[act].get("values", {})
          for v, fq in sorted(vals.items(), key=lambda x: x[1], reverse=True):
            st.text(f"{v} — ({fq} раз)")

# ВКЛАДКА 4: ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
with tab_required:
  st.subheader("⭐ Обязательные поля")
  cats = db["categories"]
  if cats:
    sel = st.selectbox("Подкатегория", sorted(cats.keys()))
    if sel:
      reqs = cats[sel].get("required_attributes", [])
      new_r = []
      for attr in db["global_glossary"].keys():
        if st.checkbox(attr, value=(attr in reqs), key=f"req_{sel}_{attr}"):
          new_r.append(attr)
      if st.button("💾 Сохранить обязательные"):
        db["categories"][sel]["required_attributes"] = new_r
        save_db(db)
        st.success("Сохранено!")
