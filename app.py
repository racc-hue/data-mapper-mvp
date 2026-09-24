import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Гибкий MDM-маппер прайсов", page_icon="🧠", layout="wide"
)

DB_FILE = "knowledge_base.json"


# Загрузка базы знаний
def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "global_attributes": {
          "Наименование товара": {"required": True},
          "Артикул / SKU": {"required": False},
          "Цена": {"required": False},
          "Габариты (ВхШхГ)": {"required": False},
      },
      "templates": {},
  }


def save_db(data):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


db = load_db()

st.title("🧠 Гибкий маппер и нормализатор характеристик")
st.write(
    "Настраивайте только те поля, которые вам нужны, и управляйте"
    " характеристиками."
)

# 1. Загрузка файла
uploaded_file = st.file_uploader(
    "Загрузите прайс-лист поставщика или выгрузку с сайта (Excel или CSV)",
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

  st.subheader("📋 Предпросмотр исходного файла")
  st.dataframe(df.head(3), use_container_width=True)
  columns = list(df.columns)

  st.divider()
  st.subheader("⚙️ Шаг 1: Выберите, какие параметры участвуют в этом маппинге")
  st.write(
      "Отметьте галочками только те характеристики, которые вам действительно"
      " нужны в этот раз. Лишнее можно отключить."
  )

  # Блок управления глобальными атрибутами прямо на экране
  all_known_attrs = list(db["global_attributes"].keys())

  selected_attributes = []
  cols_checkboxes = st.columns(min(len(all_known_attrs), 4))
  for idx, attr in enumerate(all_known_attrs):
    col_idx = idx % len(cols_checkboxes)
    with cols_checkboxes[col_idx]:
      # По умолчанию выбираем обязательные или основные
      is_default = db["global_attributes"][attr].get("required", False) or attr in [
          "Наименование товара",
          "Артикул / SKU",
      ]
      if st.checkbox(attr, value=is_default, key=f"chk_{attr}"):
        selected_attributes.append(attr)

  # Возможность добавить совершенно новый заголовок на лету
  with st.expander("➕ Добавить новый глобальный заголовок в систему"):
    new_attr_input = st.text_input("Название новой характеристики (например, 'Диаметр, мм')")
    is_new_req = st.checkbox("Сделать это поле обязательным для сайта")
    if st.button("Создать характеристику"):
      if new_attr_input and new_attr_input not in db["global_attributes"]:
        db["global_attributes"][new_attr_input] = {"required": is_new_req}
        save_db(db)
        st.success(f"Характеристика '{new_attr_input}' добавлена! Перезагрузите выбор.")
        st.rerun()

  st.divider()
  st.subheader("🔗 Шаг 2: Сопоставление колонок и просмотр значений")

  # Выбор сохраненного шаблона
  template_names = list(db["templates"].keys())
  selected_template = st.selectbox(
      "📦 Загрузить сохраненный шаблон маппинга для этого поставщика",
      ["-- Выберите шаблон (опционально) --"] + template_names,
  )

  saved_mapping = {}
  if selected_template != "-- Выберите шаблон (опционально) --":
    saved_mapping = db["templates"][selected_template]

  mapping_results = {}

  # Выстраиваем интерактивную таблицу маппинга для выбранных атрибутов
  for attr_name in selected_attributes:
    is_req = db["global_attributes"].get(attr_name, {}).get("required", False)
    label_text = f"**{attr_name}**" + (" *" if is_req else "")

    with st.container():
      c1, c2, c3 = st.columns([2, 3, 3])

      with c1:
        st.markdown(label_text, unsafe_allow_html=True)

      with c2:
        # Ищем дефолт из шаблона или подбираем по похожести
        default_idx = 0
        saved_col = saved_mapping.get(attr_name)
        if saved_col in columns:
          default_idx = columns.index(saved_col)
        else:
          # Пробуем найти частичное совпадение имени
          for i, col in enumerate(columns):
            if attr_name.lower() in col.lower():
              default_idx = i
              break

        chosen_col = st.selectbox(
            f"Колонка для {attr_name}",
            columns,
            index=default_idx,
            key=f"map_{attr_name}",
        )
        mapping_results[attr_name] = chosen_col

      with c3:
        # ВЫПАДАЮЩИЙ СПИСОК / ПРОСМОТР ВСЕХ УНИКАЛЬНЫХ ЗНАЧЕНИЙ ХАРАКТЕРИСТИК
        if chosen_col and chosen_col in df.columns:
          unique_values = df[chosen_col].dropna().unique().tolist()
          with st.expander(f"👁️ Посмотреть значения ({len(unique_values)} шт.)"):
            # Выводим список уникальных значений для этой характеристики
            st.write(unique_values[:100])  # показываем до 100 уникальных
            if len(unique_values) > 100:
              st.caption("Показаны первые 100 уникальных значений...")
        else:
          st.caption("Нет данных")

      st.markdown("---")

  # --- БЛОК СОХРАНЕНИЯ ШАБЛОНА ---
  st.subheader("💾 Шаг 3: Сохранение настроек маппинга")
  template_name_input = st.text_input(
      "Имя шаблона для сохранения (например, 'Поставщик_А_Прайс')", value=""
  )
  save_template_btn = st.checkbox(
      "Сохранить этот набор связок в постоянную память приложения", value=True
  )

  if st.button(
      "🚀 Проверить и сформировать итоговый файл для сайта", type="primary"
  ):
    # Сохранение шаблона в JSON
    if save_template_btn and template_name_input:
      db["templates"][template_name_input] = mapping_results
      save_db(db)
      st.success(f"Шаблон '{template_name_input}' успешно сохранен в память!")

    # Валидация обязательных полей
    errors = []
    for attr_name in selected_attributes:
      is_req = db["global_attributes"].get(attr_name, {}).get("required", False)
      if is_req:
        mapped_col = mapping_results.get(attr_name)
        if mapped_col and df[mapped_col].isnull().any():
          errors.append(
              f"В обязательном поле '{attr_name}' (колонка файла:"
              f" '{mapped_col}') есть пустые ячейки!"
          )

    if errors:
      st.warning("⚠️ Предупреждения по обязательным полям:")
      for err in errors:
        st.write(f"- {err}")

    # Сборка итогового файла
    result_df = pd.DataFrame()
    for attr_name, mapped_col in mapping_results.items():
      if mapped_col in df.columns:
        result_df[attr_name] = df[mapped_col]

    st.success("✅ Готово! Файл успешно отформатирован под ваши параметры.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
      result_df.to_excel(writer, index=False, sheet_name="Import")

    st.download_button(
        label="📥 Скачать готовый файл",
        data=buffer.getvalue(),
        file_name="mapped_export.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
else:
  st.info("👆 Загрузите файл выгрузки или прайса выше, чтобы начать настройку.")
