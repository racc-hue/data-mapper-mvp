import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM-Система каталога и глоссария", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v2.json"


# Загрузка базы знаний (памяти)
def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "categories": {},  # { "Подкатегория": { "required_attributes": [...] } }
      "global_glossary": {},  # { "Название характеристики": [список уникальных значений] }
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

st.title("🧠 MDM-Система: Глоссарий, Характеристики и Обязательные поля")

tab_import, tab_glossary, tab_required = st.tabs([
    "📥 Загрузка файла и сбор характеристик",
    "📚 Управление глоссарием и заголовками",
    "⭐ Настройка обязательных полей",
])

# ==========================================
# ВКЛАДКА 1: ЗАГРУЗКА И СБОР ЗНАЧЕНИЙ
# ==========================================
with tab_import:
  st.subheader("Импорт файла выгрузки сайта")
  st.write(
      "Загрузите файл. Приложение автоматически отделит базовые колонки от"
      " характеристик, определит подкатегорию по `breadcrumbs` и «съест» все"
      " непустые значения характеристик в глобальный глоссарий."
  )

  uploaded_file = st.file_uploader(
      "Загрузите Excel или CSV выгрузку", type=["xlsx", "xls", "csv"], key="up_1"
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
        )
      else:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
      st.error(f"Ошибка чтения файла: {e}")
      st.stop()

    st.success(f"Файл успешно загружен. Строк: {len(df)}, Колонок: {len(df.columns)}")

    # Определяем категорию по хлебным крошкам
    cat_col = None
    for c in df.columns:
      if "breadcrumb" in c.lower() or "крошк" in c.lower() or "раздел" in c.lower():
        cat_col = c
        break

    extracted_cat = "Общий каталог"
    if cat_col and cat_col in df.columns:
      sample_bc = df[cat_col].dropna().astype(str).values
      if len(sample_bc) > 0:
        parts = sample_bc[0].split(">")
        extracted_cat = parts[-1].strip()

    st.info(f"📂 Определенная подкатегория: **{extracted_cat}**")

    # Кнопка обработки и наполнения глоссария
    if st.button("🚀 Обработать файл и закинуть характеристики в глоссарий", type="primary"):
      base_keywords = db["base_columns"]

      # Инициализируем категорию в базе, если её нет
      if extracted_cat not in db["categories"]:
        db["categories"][extracted_cat] = {"required_attributes": []}

      added_count = 0
      for col in df.columns:
        col_lower = str(col).lower()
        # Проверяем, является ли колонка характеристикой (не базовой)
        is_base = any(kw in col_lower for kw in base_keywords)

        if not is_base:
          # «Съедаем» все непустые значения из этой колонки
          non_empty_vals = df[col].dropna().astype(str).unique().tolist()
          # Убираем пустые строки или пробелы
          non_empty_vals = [v.strip() for v in non_empty_vals if v.strip()]

          if non_empty_vals:
            if col not in db["global_glossary"]:
              db["global_glossary][col] = []

            # Добавляем уникальные значения без дублей
            for val in non_empty_vals:
              if val not in db["global_glossary"][col]:
                db["global_glossary"][col].append(val)
            added_count += 1

      save_db(db)
      st.success(
          f"✅ Готово! Обработано характеристик: {added_count}. Все уникальные"
          " значения успешно добавлены в глобальный глоссарий."
      )

# ==========================================
# ВКЛАДКА 2: УПРАВЛЕНИЕ ГЛОССАРИЕМ И ЗАГОЛОВКАМИ
# ==========================================
with tab_glossary:
  st.subheader("📚 Редактор глобального глоссария характеристик")
  st.write(
      "Здесь вы можете настраивать заголовки, удалять ненужные мусорные"
      " характеристики и смотреть накопленные значения."
  )

  glossary = db["global_glossary"]

  if not glossary:
    st.info("Глоссарий пока пуст. Загрузите файл на первой вкладке.")
  else:
    to_delete = []
    for attr_name, values_list in list(glossary.items()):
      with st.expander(f"📌 {attr_name} (Уникальных значений: {len(values_list)})"):
        # Переименование заголовка характеристики
        new_name = st.text_input(
            "Переименовать заголовок", value=attr_name, key=f"rename_{attr_name}"
        )
        if new_name != attr_name and new_name:
          if st.button("💾 Сохранить новое имя", key=f"btn_rename_{attr_name}"):
            glossary[new_name] = glossary.pop(attr_name)
            save_db(db)
            st.success("Заголовок переименован!")
            st.rerun()

        st.write("Список «съеденных» значений:")
        st.write(values_list[:50])  # показываем первые 50

        if st.button("🗑️ Удалить этот заголовок и все его значения", key=f"del_g_{attr_name}"):
          to_delete.append(attr_name)

      st.write("---")

    if to_delete:
      for item in to_delete:
        glossary.pop(item, None)
      save_db(db)
      st.success("Заголовок удален из глоссария!")
      st.rerun()

# ==========================================
# ВКЛАДКА 3: НАСТРОЙКА ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ
# ==========================================
with tab_required:
  st.subheader("⭐ Независимая настройка обязательных полей по подкатегориям")
  st.write(
      "Выделите, какие именно заголовки характеристик являются обязательными"
      " для конкретной подкатегории."
  )

  categories = db["categories"]

  if not categories:
    st.info("Категории еще не зарегистрированы. Загрузите файлы выгрузки.")
  else:
    selected_cat = st.selectbox(
        "Выберите подкатегорию для настройки обязательных полей",
        list(categories.keys()),
        key="req_cat_select",
    )

    if selected_cat:
      current_reqs = categories[selected_cat].get("required_attributes", [])
      all_attrs = list(db["global_glossary"].keys())

      st.write(f"Настройка обязательных полей для категории: **{selected_cat}**")

      new_reqs = []
      for attr in all_attrs:
        is_checked = attr in current_reqs
        if st.checkbox(attr, value=is_checked, key=f"chk_req_{selected_cat}_{attr}"):
          new_reqs.append(attr)

      if st.button("💾 Сохранить обязательные поля для категории"):
        db["categories"][selected_cat]["required_attributes"] = new_reqs
        save_db(db)
        st.success(f"Обязательные поля для категории '{selected_cat}' сохранены!")

  st.write("---")
  if st.button("🗑️ Полный сброс всей базы данных"):
    if os.path.exists(DB_FILE):
      os.remove(DB_FILE)
    st.success("База данных очищена!")
    st.rerun()
