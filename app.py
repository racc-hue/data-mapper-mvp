import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM-Система каталога и глоссария", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v4.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "categories": {},  # { "Категория": { "required_attributes": [] } }
      "breadcrumbs_tree": [],  # Все цепочки хлебных крошек
      "global_glossary": {},  # { "Характеристика": { "values": [...], "is_numeric": False } }
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

    # Поиск хлебных крошек
    cat_col = None
    for c in df.columns:
      if "breadcrumb" in c.lower() or "крошк" in c.lower() or "раздел" in c.lower():
        cat_col = c
        break

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
              db["global_glossary"][col] = {"values": [], "is_numeric": False}

            # Проверяем, являются ли все значения числовыми
            all_numeric = True
            for v in vals:
              cleaned_v = (
                  v.replace(",", ".").replace(" ", "").replace("%", "")
              )
              try:
                float(cleaned_v)
              except ValueError:
                all_numeric = False
                break

            # Если колонка чисто числовая, ставим флаг is_numeric (но сохранять в словарь сами значения не обязательно, либо держим пустыми)
            if all_numeric:
              db["global_glossary"][col]["is_numeric"] = True
            else:
              for v in vals:
                if v not in db["global_glossary"][col]["values"]:
                  db["global_glossary"][col]["values"].append(v)

            added_attrs += 1

      save_db(db)
      st.success(
          f"✅ Успешно! Обработано характеристик: {added_attrs}. Глоссарий"
          " обновлен."
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
    # Формируем красивые подписи для селектора (с количеством или плашкой "только числовые")
    attr_options = []
    attr_map = {}
    for attr, info in glossary.items():
      is_num = info.get("is_numeric", False)
      if is_num:
        label = f"{attr} [только числовые]"
      else:
        count = len(info.get("values", []))
        label = f"{attr} ({count} знач.)"
      attr_options.append(label)
      attr_map[label] = attr

    col_sel, col_del_btn = st.columns([5, 1])

    with col_sel:
      selected_label = st.selectbox(
          "Выберите характеристику", attr_options, key="glossary_sel"
      )

    selected_attr = attr_map[selected_label]
    attr_info = glossary[selected_attr]

    # Возможность удалить характеристику в один клик через корзину прямо рядом
    with col_del_btn:
      st.write("")
      st.write("")
      if st.button("🗑️ Удалить", key=f"quick_del_{selected_attr}"):
        glossary.pop(selected_attr, None)
        save_db(db)
        st.success(f"Заголовок '{selected_attr}' удален!")
        st.rerun()

    # Блок настроек выбранной характеристики
    st.markdown("---")
    c1, c2 = st.columns([3, 2])

    with c1:
      new_attr_title = st.text_input(
          "Переименовать заголовок",
          value=selected_attr,
          key=f"ren_{selected_attr}",
      )
      if new_attr_title != selected_attr and new_attr_title:
        if st.button("💾 Сохранить новое имя"):
          glossary[new_attr_title] = glossary.pop(selected_attr)
          save_db(db)
          st.success("Переименовано!")
          st.rerun()

    with c2:
      st.write("**Тип данных характеристики:**")
      current_is_numeric = attr_info.get("is_numeric", False)
      new_is_numeric = st.checkbox(
          "🔢 Считать эту характеристику числовой",
          value=current_is_numeric,
          key=f"num_chk_{selected_attr}",
          help=(
              "Если включено, значения не будут забиваться в список, а заголовок"
              " получит статус '[только числовые]'. Отключите, если число нужно"
              " обрабатывать как текст."
          ),
      )
      if new_is_numeric != current_is_numeric:
        attr_info["is_numeric"] = new_is_numeric
        if new_is_numeric:
          attr_info["values"] = []  д
        save_db(db)
        st.success("Тип данных обновлен!")
        st.rerun()

    # Список значений (если характеристика не чисто числовая)
    if not attr_info.get("is_numeric", False):
      values_list = attr_info.get("values", [])
      st.markdown(
          f"**Уникальных текстовых значений:** `{len(values_list)}`"
      )

      with st.expander("👁️ Посмотреть и точечно удалить значения"):
        if not values_list:
          st.info("Список значений пуст.")
        else:
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
              attr_info["values"].remove(v)
            save_db(db)
            st.success("Значения удалены!")
            st.rerun()
    else:
      st.info(
          "ℹ️ Эта характеристика помечена как числовая. Текстовые значения"
          " не хранятся."
      )

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
