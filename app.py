import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MDM-Система каталога и глоссария", page_icon="🧠", layout="wide"
)

DB_FILE = "mdm_knowledge_base.json"


# Инициализация или загрузка постоянной базы знаний
def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "categories": {},  # { "Название подкатегории": { "required_attributes": [...] } }
      "global_attributes": [],  # Общий список всех встреченных характеристик
      "imported_files_count": 0,
  }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


db = load_db()

st.title("🧠 MDM-Система каталога, категорий и глоссария")

# Навигация по разделам
tab_import, tab_glossary = st.tabs(
    ["📥 Загрузка и обучение по файлу", "📚 Управление глоссарием и категориями"]
)

# ==========================================
# ВКЛАДКА 1: ЗАГРУЗКА И ОБУЧЕНИЕ
# ==========================================
with tab_import:
  st.subheader("Обучение системы на файле выгрузки сайта")
  st.write(
      "Загрузите выгрузку. Система автоматически определит базовые колонки,"
      " вычленит категорию из `breadcrumbs` и пополнит общий глоссарий"
      " характеристик."
  )

  uploaded_file = st.file_uploader(
      "Загрузите Excel или CSV выгрузку", type=["xlsx", "xls", "csv"], key="uploader_main"
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

    st.success(f"Файл успешно прочитан! Строк: {len(df)}, Колонок: {len(df.columns)}")
    columns = list(df.columns)

    # 1. Поиск базовых колонок и характеристик
    # Базовыми считаем те, что часто встречаются (артикул, бренд, описание, url, breadcrumbs и т.д.)
    base_keywords = [
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
    ]

    detected_base = []
    detected_chars = []

    for col in columns:
      col_lower = str(col).lower()
      is_base = any(kw in col_lower for kw in base_keywords)
      if is_base:
        detected_base.append(col)
      else:
        detected_chars.append(col)

    st.write("---")
    st.info(
        f"🔍 **Автоматический анализ структуры:**\n"
        f"- Базовые системные колонки ({len(detected_base)} шт.): `{detected_base}`\n"
        f"- Колонки характеристик ({len(detected_chars)} шт.): `{detected_chars}`"
    )

    # 2. Анализ хлебных крошек (breadcrumbs)
    category_col = None
    for col in columns:
      if "breadcrumb" in col.lower() or "крошк" in col.lower() or "раздел" in col.lower():
        category_col = col
        break

    extracted_category = "Общий каталог"
    if category_col and category_col in df.columns:
      # Берем первое непустое значение для примера
      sample_bc = df[category_col].dropna().astype(str).values
      if len(sample_bc) > 0:
        # Обычно разделитель " > "
        parts = sample_bc[0].split(">")
        extracted_category = parts[-1].strip()

    st.write(f"📂 **Определенная подкатегория для этого файла:** `{extracted_category}`")

    # Кнопка обучения и сохранения в БД
    if st.button("🚀 Обучить систему и добавить характеристики в глоссарий", type="primary"):
      # Добавляем характеристики в глобальный глоссарий (без дублей)
      for char in detected_chars:
        if char not in db["global_attributes"]:
          db["global_attributes"].append(char)

      # Регистрируем категорию, если её еще нет
      if extracted_category not in db["categories"]:
        db["categories"][extracted_category] = {"required_attributes": []}

      db["imported_files_count"] += 1
      save_db(db)
      st.success(
          f"✅ База знаний успешно обновлена! Добавлено новых характеристик в"
          f" глоссарий: {len(detected_chars)}. Категория '{extracted_category}'"
          f" зарегистрирована."
      )

# ==========================================
# ВКЛАДКА 2: УПРАВЛЕНИЕ ГЛОССАРИЕМ И КАТЕГОРИЯМИ
# ==========================================
with tab_glossary:
  st.subheader("📚 Редактор глобального глоссария и требований подкатегорий")
  st.write(
      "Здесь вы можете управлять накопленными характеристиками, удалять лишний"
      " мусор и настраивать обязательные заголовки для конкретных подкатегорий."
  )

  col_g1, col_g2 = st.columns(2)

  # Управление глобальным списком характеристик
  with col_g1:
    st.markdown("### 🌐 Общий глоссарий характеристик")
    st.caption("Все характеристики, собранные из загруженных файлов.")

    global_attrs = db["global_attributes"]
    if not global_attrs:
      st.info("Глоссарий пока пуст. Загрузите файл на первой вкладке.")
    else:
      # Интерфейс удаления ненужных заголовков
      to_remove = []
      for attr in global_attrs:
        c_a, c_b = st.columns([4, 1])
        with c_a:
          st.text(attr)
        with c_b:
          if st.button("🗑️", key=f"del_{attr}"):
            to_remove.append(attr)

      if to_remove:
        for item in to_remove:
          db["global_attributes"].remove(item)
        save_db(db)
        st.success("Характеристика удалена из глоссария!")
        st.rerun()

      # Ручное добавление характеристики в глоссарий
      st.write("---")
      new_manual_attr = st.text_input("Добавить характеристику вручную")
      if st.button("Добавить в глоссарий"):
        if new_manual_attr and new_manual_attr not in db["global_attributes"]:
          db["global_attributes"].append(new_manual_attr)
          save_db(db)
          st.success("Добавлено!")
          st.rerun()

  # Управление категориями и их обязательными полями
  with col_g2:
    st.markdown("### 📂 Подкатегории и обязательные поля")
    st.caption("Настройте, какие характеристики обязательны для каждой подкатегории.")

    categories = db["categories"]
    if not categories:
      st.info("Категорий пока нет. Они появятся после загрузки файлов с `breadcrumbs`.")
    else:
      selected_cat = st.selectbox("Выберите подкатегорию для настройки", list(categories.keys()))

      if selected_cat:
        st.write(f"Настройка обязательных полей для: **{selected_cat}**")
        current_required = categories[selected_cat].get("required_attributes", [])

        # Чекбоксы для каждой характеристики из глобального глоссария
        new_required_list = []
        for attr in db["global_attributes"]:
          is_checked = attr in current_required
          if st.checkbox(attr, value=is_checked, key=f"req_{selected_cat}_{attr}"):
            new_required_list.append(attr)

        if st.button("💾 Сохранить обязательные поля для категории"):
          db["categories"][selected_cat]["required_attributes"] = new_required_list
          save_db(db)
          st.success(f"Требования для категории '{selected_cat}' сохранены!")

  st.write("---")
  if st.button("🗑️ Сбросить всю базу данных (очистить память)"):
    if os.path.exists(DB_FILE):
      os.remove(DB_FILE)
    st.success("База данных очищена!")
    st.rerun()
