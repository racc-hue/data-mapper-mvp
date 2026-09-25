import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Маппинг фидов поставщика", page_icon="🔗", layout="wide"
)

DB_FILE = "mdm_knowledge_base_v10.json"


def load_db():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return None


db = load_db()

st.title("🔗 Маппинг и сопоставление характеристик фида поставщика")

if not db:
  st.error(
      f"⚠️ База данных (`{DB_FILE}`) не найдена! Сначала загрузите выгрузку на"
      " главной странице."
  )
  st.stop()

base_columns = db.get("base_columns", [
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
])

glossary = db.get("global_glossary", {})
sorted_glossary_attrs = sorted(
    glossary.keys(),
    key=lambda k: glossary[k].get("total_filled", 0),
    reverse=True,
)

all_target_options = (
    ["— Пропустить / Не выгружать —"] + base_columns + sorted_glossary_attrs
)

st.subheader("1. Загрузка фида поставщика")
uploaded_feed = st.file_uploader(
    "Загрузите Excel или CSV фид поставщика", type=["xlsx", "xls", "csv"]
)

if uploaded_feed is not None:
  try:
    if uploaded_feed.name.endswith(".csv"):
      raw_bytes = uploaded_feed.read()
      text_data = None
      for enc in ["utf-8-sig", "cp1251", "utf-8", "latin1"]:
        try:
          text_data = raw_bytes.decode(enc)
          break
        except UnicodeDecodeError:
          continue
      df_feed = pd.read_csv(
          io.StringIO(text_data),
          sep=None,
          engine="python",
          encoding_errors="replace",
          on_bad_lines="skip",
      )
    else:
      df_feed = pd.read_excel(uploaded_feed)
  except Exception as e:
    st.error(f"Ошибка чтения файла фида: {e}")
    st.stop()

  st.success(
      f"Файл успешно загружен. Строк: {len(df_feed)}, Колонок:"
      f" {len(df_feed.columns)}"
  )

  st.markdown("---")
  st.subheader("2. Настройка соответствия (маппинг) колонок")
  st.info(
      "💡 Колонки со схожими названиями сопоставились автоматически. Остальные"
      " можно выбрать из выпадающего списка (отсортированы по частотности в"
      " базе)."
  )

  mapping_results = {}
  feed_columns = list(df_feed.columns)

  for i in range(0, len(feed_columns), 2):
    row_cols = st.columns(2)
    for j in range(2):
      if i + j < len(feed_columns):
        feed_col = feed_columns[i + j]
        with row_cols[j]:
          default_index = 0
          feed_col_lower = str(feed_col).strip().lower()
          for idx, opt in enumerate(all_target_options):
            if opt.lower() == feed_col_lower:
              default_index = idx
              break

          selected_target = st.selectbox(
              f"Колонка в фиде: `{feed_col}`",
              options=all_target_options,
              index=default_index,
              key=f"map_{feed_col}",
          )
          mapping_results[feed_col] = selected_target

  st.markdown("---")
  st.subheader("3. Генерация и выгрузка итогового файла")

  if st.button("🚀 Преобразовать фид по шаблону базы", type="primary"):
    new_df_data = {}
    renamed_count = 0

    for feed_col, target_col in mapping_results.items():
      if target_col != "— Пропустить / Не выгружать —":
        if target_col in new_df_data:
          new_df_data[target_col] = (
              new_df_data[target_col].astype(str)
              + ", "
              + df_feed[feed_col].astype(str)
          )
        else:
          new_df_data[target_col] = df_feed[feed_col]
          renamed_count += 1

    df_mapped = pd.DataFrame(new_df_data)

    for col in base_columns:
      if col not in df_mapped.columns:
        df_mapped[col] = ""

    existing_bases = [c for c in base_columns if c in df_mapped.columns]
    other_cols = [c for c in df_mapped.columns if c not in base_columns]
    df_final = df_mapped[existing_bases + other_cols]

    st.success(
        f"✅ Успешно сопоставлено колонок: {renamed_count}. Итоговых строк:"
        f" {len(df_final)}"
    )

    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
      df_final.to_excel(writer, index=False, sheet_name="Mapped_Feed")
    output_buffer.seek(0)

    st.download_button(
        label="📥 Скачать готовый файл выгрузки (.xlsx)",
        data=output_buffer,
        file_name="processed_supplier_feed.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
