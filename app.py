import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM-Система каталога и глоссария", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v3.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "categories": {},  # { "Категория": { "required_attributes": [] } }
      "breadcrumbs_tree": [],  # Все уникальные цепочки хлебных крошек
      "global_glossary": {},  # { "Характеристика": [значение1, значение2, ...] }
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

st.title("🧠 MDM-Система управления каталогом и глоссарием")

tab_import, tab_structure, tab_glossary, tab_required = st.tabs([
    "📥 Загрузка файлов",
    "📂 Структура и категории",
    "📚 Глоссарий и значения",
    "⭐ Обязательные поля",
])

# ==========================================
# ВКЛАДКА 1: ЗАГРУЗКА ФАЙЛОВ
# ==========================================
with tab_import:
  st.subheader("Импорт файлов выгрузки сайта")
  st.write(
      "Загрузите файл. Система автоматически разберет базовые колонки,"
      " пополнит дерево структуры из `breadcrumbs` и соберет все значения"
      " характеристик в компактный глоссарий."
  )

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

    st.success(f"Файл загружен. Строк: {len(df)}, Колонок: {len(df.columns)}")

    # Поиск хлебных крошек и структуры
    cat_col = None
    for c in df.columns:
      if "breadcrumb" in c.lower() or "крошк" in c.lower() or "раздел" in c.lower():
        cat_col = c
        break

    extracted_cat = "Общий каталог"
    full_bc_chains = []
    if cat_col and cat_col in df.columns:
      unique_bcs = df[cat_col].dropna().astype(str).unique().tolist()
      for bc in unique_bcs:
        if bc not in full_bc_chains:
          full_bc_chains.append(bc)
        parts = bc.split(">")
        leaf_cat = parts[-1].strip()
        if leaf_cat not in db["categories"]:
          db["categories"][leaf_cat] = {"required_attributes": []}

    st.info(f"📂 Найдено уникальных цепочек крошек в файле: {len(full_bc_chains)}")

    if st.button("🚀 Обработать файл и обновить базу данных", type="primary"):
      for chain in full_bc_chains:
        if chain not in db["breadcrumbs_tree"]:
          db["breadcrumbs_tree"].append(chain)

      base_keywords = db["base_columns"]
      added_attrs = 0

      for col in df.columns:
        col_lower = str(col).lower()
        is_base = any(kw in col_lower for kw in base_keywords)
        if not is_base:
          vals = df[col].dropna().astype(str).unique().tolist()
          vals = [v.strip() for v in vals if v.strip()]
          if vals:
            if col not in db["global_glossary"]:
              db["global_glossary"][col] = []
            for v in vals:
              if v not in db["global_glossary"][col]:
                db["global_glossary"][col].append(v)
            added_attrs += 1

      save_db(db)
      st.success(
          f"✅ Успешно! Добавлено/обновлено характеристик: {added_attrs}."
          " Структура и глоссарий расширены."
      )

# ==========================================
# ВКЛАДКА 2: СТРУКТУРА И КАТЕГОРИИ
# ==========================================
with tab_structure:
  st.subheader("📂 Дерево структуры и подкатегории")
  col_s1, col_s2 = st.columns(2)

  with col_s1:
    st.markdown("### 🌲 Накопленные цепочки `breadcrumbs`")
    if not db["breadcrumbs_tree"]:
      st.info("Цепочки пока не загружены.")
    else:
      for idx, chain in enumerate(db["breadcrumbs_tree"], 1):
        st.code(f"{idx}. {chain}")

  with col_s2:
    st.markdown("### 📑 Зарегистрированные подкатегории")
    categories = db["categories"]
    if not categories:
      st.info("Подкатегории появятся после загрузки файлов.")
    else:
      for cat_name in categories.keys():
        st.markdown(f"- 📁 **{cat_name}**")

# ==========================================
# ВКЛАДКА 3: ГЛОССАРИЙ И ЗНАЧЕНИЯ
# ==========================================
with tab_glossary:
  st.subheader("📚 Компактный редактор глоссария и значений")
  glossary = db["global_glossary"]

  if not glossary:
    st.info("Глоссарий пуст. Загрузите файл на первой вкладке.")
  else:
    selected_attr = st.selectbox(
        "Выберите характеристику для управления значениями", list(glossary.keys())
    )

    if selected_attr:
      values_list = glossary[selected_attr]

      col_g1, col_g2 = st.columns([3, 1])
      with col_g1:
        new_attr_title = st.text_input(
            "Переименовать заголовок",
            value=selected_attr,
            key=f"ren_{selected_attr}",
        )
      with col_g2:
        st.write("")
        st.write("")
        if new_attr_title != selected_attr and new_attr_title:
          if st.button("💾 Сохранить имя"):
            glossary[new_attr_title] = glossary.pop(selected_attr)
            save_db(db)
            st.success("Переименовано!")
            st.rerun()

      st.markdown(
          f"**Уникальных значений в характеристике:** `{len(values_list)}`"
      )

      with st.expander(
          "👁️ Посмотреть и отредактировать значения (удалить лишнее)"
      ):
        vals_to_remove = []
        for val in values_list:
          c_v1, c_v2 = st.columns([5, 1])
          with c_v1:
            st.text(val)
          with c_v2:
            if st.button("❌", key=f"del_val_{selected_attr}_{val}"):
              vals_to_remove.append(val)

        if vals_to_remove:
          for v in vals_to_remove:
            glossary[selected_attr].remove(v)
          save_db(db)
          st.success("Значение(я) удалены!")
          st.rerun()

      st.write("---")
      if st.button(
          f"🗑️ Удалить весь заголовок '{selected_attr}' из глоссария",
          type="secondary",
      ):
        glossary.pop(selected_attr, None)
        save_db(db)
        st.success("Заголовок полностью удален!")
        st.rerun()

# ==========================================
# ВКЛАДКА 4: ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
# ==========================================
with tab_required:
  st.subheader("⭐ Настройка обязательных полей по подкатегориям")
  categories = db["categories"]

  if not categories:
    st.info("Сначала загрузите файлы, чтобы появились подкатегории.")
  else:
    selected_cat = st.selectbox(
        "Выберите подкатегорию", list(categories.keys()), key="req_box"
    )

    if selected_cat:
      current_reqs = categories[selected_cat].get("required_attributes", [])
      all_attrs = list(db["global_glossary"].keys())

      st.write(
          "Отметьте галочками заголовки, которые должны быть обязательными"
          f" для подкатегории **{selected_cat}**:"
      )

      new_reqs = []
      for attr in all_attrs:
        is_checked = attr in current_reqs
        if st.checkbox(attr, value=is_checked, key=f"req_c_{selected_cat}_{attr}"):
          new_reqs.append(attr)

      if st.button("💾 Сохранить обязательные поля"):
        db["categories"][selected_cat]["required_attributes"] = new_reqs
        save_db(db)
        st.success("Изменения сохранены!")

  st.write("---")
  if st.button("🗑️ Полный сброс базы данных"):
    if os.path.exists(DB_FILE):
      os.remove(DB_FILE)
    st.success("База очищена!")
    st.rerun()
