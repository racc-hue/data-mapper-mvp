import io
import json
import os
from collections import Counter
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM-Система каталога и глоссария", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v9.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "categories": {},  # { "Полный путь": { "required_attributes": [] } }
      "breadcrumbs_tree": [],  # Все уникальные цепочки хлебных крошек
      "global_glossary": {},  # Глоссарий характеристик
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
      # Проходим по всем ячейкам колонки категорий
      unique_cells = df[cat_col].dropna().astype(str).unique().tolist()
      for cell in unique_cells:
        # Товар может принадлежать нескольким веткам, разделенным точкой с запятой ';'
        sub_branches = cell.split(";")
        for branch in sub_branches:
          parts = [p.strip() for p in branch.split(">") if p.strip()]
          if not parts:
            continue
          normalized_chain = " > ".join(parts)

          if normalized_chain not in full_bc_chains:
            full_bc_chains.append(normalized_chain)

          # Регистрируем каждый уровень иерархии в базе категорий
          current_path = []
          for part in parts:
            current_path.append(part)
            path_str = " > ".join(current_path)
            if path_str not in db["categories"]:
              db["categories"][path_str] = {"required_attributes": []}

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
          col_series = df[col].dropna()
          vals_raw = col_series.astype(str).tolist()
          vals_raw = [v.strip() for v in vals_raw if v.strip()]
          filled_count = len(vals_raw)

          if filled_count > 0:
            if col not in db["global_glossary"]:
              db["global_glossary"][col] = {
                  "values": {},
                  "is_numeric": False,
                  "total_filled": 0,
              }

            db["global_glossary"][col]["total_filled"] = (
                db["global_glossary"][col].get("total_filled", 0) + filled_count
            )
            val_counts = Counter(vals_raw)

            all_numeric = True
            for v in val_counts.keys():
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
              if isinstance(db["global_glossary"][col]["values"], list):
                old_list = db["global_glossary"][col]["values"]
                db["global_glossary"][col]["values"] = {
                    v: 1 for v in old_list
                }

              for v, cnt in val_counts.items():
                current_dict = db["global_glossary"][col]["values"]
                current_dict[v] = current_dict.get(v, 0) + cnt

            added_attrs += 1

      save_db(db)
      st.success(
          f"✅ Успешно! Обработано характеристик: {added_attrs}. Глоссарий"
          " обновлен."
      )

# ==========================================
# ВКЛАДКА 2: СТРУКТУРА И КАТЕГОРИИ (ИЕРАРХИЧЕСКОЕ ДЕРЕВО)
# ==========================================
with tab_structure:
  st.subheader("📂 Иерархическое дерево структуры каталога")
  categories = db["categories"]

  if not categories:
    st.info("Сначала загрузите файлы, чтобы сформировать структуру.")
  else:

    def build_tree(chains):
      tree = {}
      for chain in chains:
        parts = [p.strip() for p in chain.split(">") if p.strip()]
        current = tree
        for part in parts:
          if part not in current:
            current[part] = {}
          current = current[part]
      return tree

    def render_tree(subtree):
      for name, sub in sorted(subtree.items()):
        has_children = len(sub) > 0
        if has_children:
          with st.expander(f"📁 {name}", expanded=False):
            render_tree(sub)
        else:
          st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 `{name}`")

    tree_dict = build_tree(db["breadcrumbs_tree"])
    render_tree(tree_dict)

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

    with col_left:
      st.markdown("### 📋 Заголовки характеристик")

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
          if st.session_state.get("active_attr") in to_delete:
            st.session_state.active_attr = None
          st.success(f"Успешно удалено заголовков: {len(to_delete)}")
          st.rerun()
        else:
          st.warning("Не выбрано ни одного заголовка для удаления.")

      st.markdown("---")

      all_attrs = list(glossary.keys())
      if (
          "active_attr" not in st.session_state
          or st.session_state.active_attr not in glossary
      ):
        st.session_state.active_attr = all_attrs[0] if all_attrs else None

      for attr in all_attrs:
        info = glossary[attr]
        is_num = info.get("is_numeric", False)
        total_filled = info.get("total_filled", 0)

        if is_num:
          badge = f"[только числовые: {total_filled} зап.]"
        else:
          vals_dict = info.get("values", {})
          if isinstance(vals_dict, list):
            vals_dict = {v: 1 for v in vals_dict}
            info["values"] = vals_dict
          unique_count = len(vals_dict)
          badge = f"({unique_count} уник. / {total_filled} зап.)"

        c_chk, c_btn = st.columns([1, 10])
        with c_chk:
          st.checkbox("", key=f"chk_attr_{attr}", label_visibility="collapsed")
        with c_btn:
          btn_type = (
              "primary"
              if st.session_state.active_attr == attr
              else "secondary"
          )
          if st.button(
              f"{attr} {badge}",
              key=f"btn_attr_{attr}",
              use_container_width=True,
              type=btn_type,
          ):
            st.session_state.active_attr = attr
            st.rerun()

    with col_right:
      active_attr = st.session_state.get("active_attr")
      if not active_attr or active_attr not in glossary:
        st.info("Выберите заголовок слева, чтобы посмотреть его характеристики.")
      else:
        st.markdown(f"### ⚙️ Редактирование: `{active_attr}`")
        attr_info = glossary[active_attr]

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
              attr_info["values"] = {}
            save_db(db)
            st.rerun()

        st.markdown(
            f"**Всего заполненных ячеек в выгрузках:**"
            f" `{attr_info.get('total_filled', 0)}`"
        )
        st.markdown("---")

        if not attr_info.get("is_numeric", False):
          vals_dict = attr_info.get("values", {})
          if isinstance(vals_dict, list):
            vals_dict = {v: 1 for v in vals_dict}
            attr_info["values"] = vals_dict

          st.markdown(
              f"**Уникальных текстовых значений:** `{len(vals_dict)}`"
          )

          if vals_dict:
            if st.button(
                "🗑️ Удалить выбранные значения",
                key=f"del_vals_{active_attr}",
            ):
              vals_to_del = [
                  v
                  for v in vals_dict.keys()
                  if st.session_state.get(
                      f"chk_val_{active_attr}_{hash(v)}", False
                  )
              ]
              if vals_to_del:
                for v in vals_to_del:
                  vals_dict.pop(v, None)
                save_db(db)
                st.success(f"Успешно удалено значений: {len(vals_to_del)}")
                st.rerun()
              else:
                st.warning("Не выбрано ни одного значения.")

            st.markdown("---")

            sorted_vals = sorted(
                vals_dict.items(), key=lambda x: x[1], reverse=True
            )
            for v, freq in sorted_vals:
              vc1, vc2 = st.columns([1, 15])
              with vc1:
                st.checkbox(
                    "",
                    key=f"chk_val_{active_attr}_{hash(v)}",
                    label_visibility="collapsed",
                )
              with vc2:
                st.text(f"{v}  —  ({freq} раз)")
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
        "Выберите подкатегорию", sorted(categories.keys()), key="req_box"
    )

    if selected_cat:
      current_reqs = categories[selected_cat].get("required_attributes", [])
      all_attrs = list(db["global_glossary"].keys())

      st.write(
          "Отметьте галочками заголовки, которые должны быть обязательными"
          f" для узла **{selected_cat}**:"
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
