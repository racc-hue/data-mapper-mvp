import json
import os
import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Умный MDM-маппер прайсов", page_icon="🧠", layout="wide"
)

# Файл для имитации базы данных / памяти приложения
DB_FILE = "knowledge_base.json"


# Загрузка базы знаний (памяти)
def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  # Дефолтная структура, если файла нет
  return {
      "global_attributes": {
          "Наименование товара": {"required": True, "synonyms": []},
          "Цена": {"required": True, "synonyms": []},
          "Артикул / SKU": {"required": False, "synonyms": []},
          "Габариты (ВхШхГ)": {"required": True, "synonyms": []},
      },
      "templates": {},
  }


# Сохранение базы знаний
def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


db = load_db()

st.title("🧠 Интеллектуальная система маппинга и памяти прайсов")
st.sidebar.header("⚙️ Управление памятью и словарем")

# --- БОКОВАЯ ПАНЕЛЬ: Управление глобальными характеристиками ---
st.sidebar.subheader("Глобальные параметры сайта")
new_attr_name = st.sidebar.text_input("Добавить новый глобальный заголовок")
new_attr_required = st.sidebar.checkbox("Обязательное поле для сайта")

if st.sidebar.button("➕ Добавить в глобальный справочник"):
  if new_attr_name and new_attr_name not in db["global_attributes"]:
    db["global_attributes"]
    db["global_attributes"][new_attr_name] = {
        "required": new_attr_required,
        "synonyms": [],
    }
    save_db(db)
    st.sidebar.success(f"Параметр '{new_attr_name}' добавлен в память!")
    st.rerun()

st.sidebar.divider()
st.sidebar.write("📌 **Текущие глобальные параметры в памяти:**")
for attr, info in db["global_attributes"].items():
  req_mark = "⭐ (обязательно)" if info["required"] else ""
  st.sidebar.text(f"- {attr} {req_mark}")


# --- ОСНОВНОЙ ЭКРАН ---
uploaded_file = st.file_uploader(
    "Загрузите прайс-лист поставщика или выгрузку (Excel / CSV)",
    type=["xlsx", "xls", "csv"],
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

  st.subheader("📋 Предпросмотр загруженного файла")
  st.dataframe(df.head(3), use_container_width=True)
  columns = list(df.columns)

  st.divider()
  st.subheader("🔗 Интерактивный маппинг и обучение")

  # Выбор сохраненного профиля (если есть)
  template_names = list(db["templates"].keys())
  selected_template = st.selectbox(
      "📦 Применить сохраненный шаблон маппинга (если есть)",
      ["-- Выберите шаблон или настройте вручную --"] + template_names,
  )

  saved_mapping = {}
  if selected_template != "-- Выберите шаблон или настройте вручную --":
    saved_mapping = db["templates"][selected_template]

  # Динамическое построение строк маппинга для каждого глобального атрибута
  mapping_results = {}

  st.markdown(
      "Сопоставьте глобальные параметры сайта с колонками в загруженном файле:"
  )

  for attr_name, attr_info in db["global_attributes"].items():
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
      req_label = (
          f"**{attr_name}** <span style='color:red'>*</span>"
          if attr_info["required"]
          else f"**{attr_name}**"
      )
      st.markdown(req_label, unsafe_allow_html=True)

    with col2:
      # Пытаемся подставить дефолт из сохраненного шаблона
      default_idx = 0
      saved_col = saved_mapping.get(attr_name)
      if saved_col in columns:
        default_idx = columns.index(saved_col)

      chosen_col = st.selectbox(
          f"Колонка для {attr_name}",
          columns,
          index=default_idx,
          key=f"map_{attr_name}",
      )
      mapping_results[attr_name] = chosen_col

    with col3:
      if chosen_col and chosen_col in df.columns:
        sample_val = str(df[chosen_col].dropna().head(1).values)
        st.caption(f"Пример: {sample_val}")
      else:
        st.caption("Нет данных")

  st.divider()

  # --- БЛОК СОХРАНЕНИЯ В ПАМЯТЬ ---
  st.subheader("💾 Сохранение настроек в память приложения")
  save_template_name = st.text_input(
      "Имя шаблона для этого поставщика (например: 'Прайс_Поставщика_А')",
      value="",
  )

  col_s1, col_s2 = st.columns(2)
  with col_s1:
    save_checked = st.checkbox(
        "Сохранить этот маппинг в постоянную память (шаблоны)", value=True
    )

  if st.button(
      "🚀 Запустить валидацию и сформировать файл",
      type="primary",
  ):
    # Если пользователь хочет сохранить шаблон
    if save_checked and save_template_name:
      db["templates"][save_template_name] = mapping_results
      save_db(db)
      st.success(f"Шаблон '{save_template_name}' успешно сохранен в память!")

    # Валидация обязательных полей
    errors = []
    for attr_name, attr_info in db["global_attributes"].items():
      if attr_info["required"]:
        mapped_col = mapping_results.get(attr_name)
        if mapped_col and df[mapped_col].isnull().any():
          errors.append(
              f"В обязательной колонке '{attr_name}' (колонка файла:"
              f" '{mapped_col}') обнаружены пустые ячейки!"
          )

    if errors:
      st.warning(
          "⚠️ Обнаружены незаполненные обязательные поля перед выгрузкой:"
      )
      for err in errors:
        st.write(f"- {err}")

    # Сборка итогового файла
    result_df = pd.DataFrame()
    for attr_name, mapped_col in mapping_results.items():
      if mapped_col in df.columns:
        result_df[attr_name] = df[mapped_col]

    st.success("✅ Готово! Файл сформирован согласно вашим настройкам.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
      result_df.to_excel(writer, index=False, sheet_name="Import")

    st.download_button(
        label="📥 Скачать готовый файл для сайта",
        data=buffer.getvalue(),
        file_name="normalized_export.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
else:
  st.info("👆 Загрузите файл выше, чтобы начать настройку маппинга.")
