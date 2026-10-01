import io
import json
import os
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Маппинг фидов и значений", page_icon="🔗", layout="wide"
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

st.title("🔗 Шаг 2: Маппинг колонок и Шаг 3: Сопоставление значений")

if not db:
  st.error(
      f"⚠️ База данных (`{DB_FILE}`) не найдена! Сначала загрузите выгрузку на"
      " главной странице."
  )
  st.stop()

# Ваши точные базовые заголовки
base_columns = [
    "артикул",
    "Код производителя",
    "название артикула 1с",
    "id карточки",
    "Карточка скрыта",
    "url",
    "Название карточки",
    "breadcrumbs",
    "бренд",
    "Описание",
    "URL основной картинки",
    "URL картинок",
    "URL индивидуальных картинок",
    "URL youtube",
    "документы",
    "сертификаты",
]

# Глоссарий характеристик, отсортированный по частотности (самые частые сверху)
glossary = db.get("global_glossary", {})
sorted_glossary_attrs = sorted(
    glossary.keys(),
    key=lambda k: glossary[k].get("total_filled", 0),
    reverse=True,
)

all_target_options = (
    ["— Пропустить / Не выгружать —"] + base_columns + sorted_glossary_attrs
)

if "step_3_ready" not in st.session_state:
  st.session_state.step_3_ready = False
if "df_mapped_final" not in st.session_state:
  st.session_state.df_mapped_final = None

# ==========================================
# ШАГ 2: МАППИНГ КОЛОНОК ФИДА
# ==========================================
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

  total_rows = len(df_feed)
  st.success(f"Файл успешно загружен. Всего строк: {total_rows}")

  st.markdown("---")
  st.subheader("2. Сопоставление заголовков (колонок)")
  st.info(
      "💡 Исходные названия колонок из фида выделены жирным. Выберите для"
      " каждой из них целевое поле из вашей базы (частотные характеристики"
      " расположены вверху списка)."
  )

  mapping_results = {}
  feed_columns = list(df_feed.columns)

  for i in range(0, len(feed_columns), 2):
    row_cols = st.columns(2)
    for j in range(2):
      if i + j < len(feed_columns):
        feed_col = feed_columns[i + j]
        with row_cols[j]:
          filled_count = df_feed[feed_col].dropna().astype(str).str.strip()
          filled_count = (filled_count != "").sum()
          fill_pct = (
              int((filled_count / total_rows) * 100) if total_rows > 0 else 0
          )

          default_index = 0
          feed_col_lower = str(feed_col).strip().lower()
          for idx, opt in enumerate(all_target_options):
            if opt.lower() == feed_col_lower:
              default_index = idx
              break

          st.markdown(
              f"📌 **`{feed_col}`** &nbsp;&nbsp;|&nbsp;&nbsp; *заполнено:"
              f" {filled_count}/{total_rows} ({fill_pct}%)*"
          )
          selected_target = st.selectbox(
              f"Выбор целевого поля для {feed_col}",
              options=all_target_options,
              index=default_index,
              key=f"map_{feed_col}",
              label_visibility="collapsed",
          )
          mapping_results[feed_col] = selected_target

  st.markdown("---")
  if st.button("🚀 Подтвердить маппинг колонок и перейти к шагу 3", type="primary"):
    new_df_data = {}
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

    df_mapped = pd.DataFrame(new_df_data)

    for col in base_columns:
      if col not in df_mapped.columns:
        df_mapped[col] = ""

    existing_bases = [c for c in base_columns if c in df_mapped.columns]
    other_cols = [c for c in df_mapped.columns if c not in base_columns]
    st.session_state.df_mapped_final = df_mapped[existing_bases + other_cols]
    st.session_state.step_3_ready = True
    st.success("✅ Колонки успешно сопоставлены! Переходим к шагу 3 ниже 👇")

# ==========================================
# ШАГ 3: СОПОСТАВЛЕНИЕ И НОРМАЛИЗАЦИЯ ЗНАЧЕНИЙ
# ==========================================
if st.session_state.step_3_ready and st.session_state.df_mapped_final is not None:
  st.markdown("---")
  st.subheader(
      "3. Шаг 3: Сопоставление и нормализация конкретных характеристик (значений)"
  )
  st.info(
      "Здесь вы можете выбрать характеристику, сопоставить значения из фида с"
      " эталоном из базы или вписать своё собственное значение вручную."
  )

  df_work = st.session_state.df_mapped_final.copy()
  non_base_cols = [c for c in df_work.columns if c not in base_columns]

  if non_base_cols:
    selected_char_col = st.selectbox(
        "Выберите характеристику для нормализации значений", non_base_cols
    )

    if selected_char_col:
      unique_vals = (
          df_work[selected_char_col]
          .dropna()
          .astype(str)
          .str.strip()
          .unique()
          .tolist()
      )
      unique_vals = [v for v in unique_vals if v and v != "nan"]

      st.write(
          f"Найдено уникальных значений в колонке `{selected_char_col}`:"
          f" `{len(unique_vals)}`"
      )

      ref_values_dict = (
          glossary.get(selected_char_col, {}).get("values", {})
          if selected_char_col in glossary
          else {}
      )
      ref_options = ["— Не менять —"] + sorted(
          ref_values_dict.keys(),
          key=lambda x: ref_values_dict[x],
          reverse=True,
      )

      value_mapping = {}
      with st.form(key=f"val_map_form_{selected_char_col}"):
        st.write(
            "Для каждого значения выберите эталон из списка **или** впишите"
            " своё:"
        )

        for val in unique_vals[:50]:
          cols_val = st.columns([2, 2, 2])
          with cols_val[0]:
            st.markdown(f"Исходное: **{val}**")
          with cols_val[1]:
            chosen_opt = st.selectbox(
                f"Эталон для {val}",
                options=ref_options,
                key=f"val_sel_{selected_char_col}_{hash(val)}",
                label_visibility="collapsed",
            )
          with cols_val[2]:
            custom_val = st.text_input(
                f"Своё значение для {val}",
                placeholder="Или введите своё...",
                key=f"custom_val_{selected_char_col}_{hash(val)}",
                label_visibility="collapsed",
            )

          if custom_val.strip():
            value_mapping[val] = custom_val.strip()
          elif chosen_opt != "— Не менять —":
            value_mapping[val] = chosen_opt

        submitted = st.form_submit_button(
            "💾 Применить замену значений к датасету"
        )
        if submitted and value_mapping:
          df_work[selected_char_col] = df_work[selected_char_col].replace(
              value_mapping
          )
          st.session_state.df_mapped_final = df_work
          st.success("✅ Значения успешно заменены в датасете!")

  st.markdown("---")
  st.subheader("4. Финальная выгрузка готового файла")
  st.info(
      "💡 В итоговом файле базовые и обязательные заголовки будут автоматически"
      " выделены цветом для удобства."
  )

  if st.button("📥 Сгенерировать и скачать файл с оформлением", type="primary"):
    df_final = st.session_state.df_mapped_final

    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
      df_final.to_excel(writer, index=False, sheet_name="Processed_Feed")

    output_buffer.seek(0)
    wb = openpyxl.load_workbook(output_buffer)
    ws = wb.active

    base_header_fill = PatternFill(
        start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
    )
    base_header_font = Font(name="Calibri", size=11, bold=True, color="006100")

    other_header_fill = PatternFill(
        start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
    )
    other_header_font = Font(name="Calibri", size=11, bold=True, color="333333")

    for col_num in range(1, ws.max_column + 1):
      cell = ws.cell(row=1, column=col_num)
      col_name = str(cell.value)
      cell.alignment = Alignment(
          horizontal="center", vertical="center", wrap_text=True
      )

      if col_name in base_columns:
        cell.fill = base_header_fill
        cell.font = base_header_font
      else:
        cell.fill = other_header_fill
        cell.font = other_header_font

    for col in ws.columns:
      max_len = max(len(str(cell.value or "")) for cell in col)
      col_letter = openpyxl.utils.get_column_letter(col[0].column)
      ws.column_dimensions[col_letter].width = max(max_len + 3, 15)

    final_output = io.BytesIO()
    wb.save(final_output)
    final_output.seek(0)

    st.download_button(
        label="📥 Скачать красиво оформленный Excel-файл (.xlsx)",
        data=final_output,
        file_name="styled_processed_supplier_feed.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
