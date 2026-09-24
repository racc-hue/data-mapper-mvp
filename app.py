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
# ВКЛАДКА 3: ГЛОССАРИЙ И ЗНАЧЕНИЯ (ДВУХКОЛОНОЧНЫЙ ИНТЕРФЕЙС)
# ==========================================
with tab_glossary:
  st.subheader("📚 Управление глоссарием и массовое удаление")
  glossary = db["global_glossary"]

  if not glossary:
    st.info("Глоссарий пуст. Загрузите файл на первой вкладке.")
  else:
    col_left, col_right = st.columns([4, 6], gap="large")

    # --- ЛЕВАЯ КОЛОНКА: Список заголовков с чекбоксами и кнопкой выбора ---
    with col_left:
      st.markdown("### 📋 Заголовки характеристик")

      # Кнопка массового удаления выбранных заголовков
      if st.button(
          "🗑️ Удалить выбранные заголовки",
          type="primary",
          key="del_selected_attrs",
      ):
        to_delete = [
            attr
            for attr in glossary.keys()
            if st.session_state.get(f"chk_attr_{attr}", False)
        ]
        if to_delete:
          for attr in to_delete:
            glossary.pop(attr, None)
          save_db(db)
          # Сбрасываем активный выбор если он был удален
          if st.session_state.get("active_attr") in to_delete:
            st.session_state.active_attr = None
          st.success(f"Успешно удалено заголовков: {len(to_delete)}")
          st.rerun()
        else:
          st.warning("Не выбрано ни одного заголовка для удаления.")

      st.markdown("---")

      # Установка активного заголовка по умолчанию
      all_attrs = list(glossary.keys())
      if (
          "active_attr" not in st.session_state
          or st.session_state.active_attr not in glossary
      ):
        st.session_state.active_attr = all_attrs[0] if all_attrs else None

      # Вывод списка заголовков
      for attr in all_attrs:
        info = glossary[attr]
        is_num = info.get("is_numeric", False)
        badge = (
            "[только числовые]"
            if is_num
            else f"({len(info.get('values', []))} знач.)"
        )

        c_chk, c_btn = st.columns([1, 10])
        with c_chk:
          st.checkbox("", key=f"chk_attr_{attr}", label_visibility="collapsed")
        with c_btn:
          # Делаем активную кнопку подсветкой
          btn_type = (
              "primary"
              if st.session_state.active_attr == attr
              else "secondary"
          )
          if st.button(f"{attr} {badge}", key=f"btn_attr_{attr}", use_container_width=True, type=btn_type):
            st.session_state.active_attr = attr
            st.rerun()

    # --- ПРАВАЯ КОЛОНКА: Детали выбранного заголовка и значений ---
    with col_right:
      active_attr = st.session_state.get("active_attr")
      if not active_attr or active_attr not in glossary:
        st.info("Выберите заголовок слева, чтобы посмотреть его характеристики.")
      else:
        st.markdown(f"### ⚙️ Редактирование: `{active_attr}`")
        attr_info = glossary[active_attr]

        # Переименование и тип данных
        rc1, rc2 = st.columns(2)
        with rc1:
          new_name = st.text_input(
              "Переименовать заголовок",
              value=active_attr,
              key=f"rename_{active_attr}",
          )
          if new_name != active_attr and new_name:
            if st.button("💾 Сохранить имя"):
              glossary[new_name] = glossary.pop(active_attr)
              save_db(db)
              st.session_state.active_attr = new_name
              st.success("Переименовано!")
              st.rerun()

        with rc2:
          st.write("**Тип данных:**")
          is_num_current = attr_info.get("is_numeric", False)
          is_num_new = st.checkbox(
              "🔢 Считать числовой",
              value=is_num_current,
              key=f"num_flag_{active_attr}",
          )
          if is_num_new != is_num_current:
            attr_info["is_numeric"] = is_num_new
            if is_num_new:
              attr_info["values"] = []
            save_db(db)
            st.rerun()

        st.markdown("---")

        # Список значений и массовое удаление
        if not attr_info.get("is_numeric", False):
          vals = attr_info.get("values", [])
          st.markdown(f"**Уникальных значений:** `{len(vals)}`")

          if vals:
            # Кнопка массового удаления выбранных значений
            if st.button(
                "🗑️ Удалить выбранные значения",
                key=f"del_vals_{active_attr}",
            ):
              vals_to_del = [
                  v
                  for v in vals
                  if st.session_state.get(
                      f"chk_val_{active_attr}_{hash(v)}", False
                  )
              ]
              if vals_to_del:
                for v in vals_to_del:
                  if v in attr_info["values"]:
                    attr_info["values"].remove(v)
                save_db(db)
                st.success(f"Успешно удалено значений: {len(vals_to_del)}")
                st.rerun()
              else:
                st.warning("Не выбрано ни одного значения.")

            st.markdown("---")

            # Список значений с чекбоксами (скроллируемая область)
            for v in vals:
              vc1, vc2 = st.columns([1, 15])
              with vc1:
                st.checkbox(
                    "",
                    key=f"chk_val_{active_attr}_{hash(v)}",
                    label_visibility="collapsed",
                )
              with vc2:
                st.text(v)
          else:
            st.info("Список значений пуст.")
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
