import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Маппер данных", page_icon="📊", layout="wide"
)

st.title("Маппер данных поставщиков")
st.write(
    "Инструмент для нормализации характеристик и подготовки данных для сайта."
)

# 1. Загрузка файла
uploaded_file = st.file_uploader(
    "Загрузите прайс-лист поставщика или выгрузку с сайта (Excel или CSV)",
    type=["xlsx", "xls", "csv"],
)

if uploaded_file is not None:
  # Читаем файл с защитой для "кривых" выгрузок со старых сайтов
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

      if text_data is None:
        raise Exception("Не удалось определить кодировку файла.")

      try:
        df = pd.read_csv(
            io.StringIO(text_data),
            sep=None,
            engine="python",
            encoding_errors="replace",
        )
      except Exception:
        df = pd.read_csv(
            io.StringIO(text_data),
            sep=";",
            engine="python",
            encoding_errors="replace",
        )
    else:
      df = pd.read_excel(uploaded_file)
  except Exception as e:
    st.error(
        f"Ошибка при чтении файла выгрузки: {e}. Попробуйте открыть этот CSV в"
        " Excel и сохранить как .xlsx"
    )
    st.stop()

  st.subheader("📋 Предпросмотр исходного файла")
  st.dataframe(df.head(5), use_container_width=True)

  columns = list(df.columns)

  st.divider()
  st.subheader("🔗 Маппинг колонок (Сопоставление)")
  st.write(
      "Свяжите колонки поставщика с глобальными системными характеристиками."
  )

  col1, col2, col3 = st.columns(3)

  with col1:
    st.markdown("**Системное поле**")
    st.text("Наименование товара *")
    st.text("Цена *")
    st.text("Артикул / SKU")
    st.text("Габариты (ВхШхГ) *")

  with col2:
    st.markdown("**Колонка у поставщика**")
    map_name = st.selectbox(
        "Название", columns, index=0 if len(columns) > 0 else 0, key="m_name"
    )
    map_price = st.selectbox(
        "Цена", columns, index=1 if len(columns) > 1 else 0, key="m_price"
    )
    map_sku = st.selectbox(
        "Артикул", columns, index=2 if len(columns) > 2 else 0, key="m_sku"
    )
    map_dims = st.selectbox(
        "Габариты", columns, index=3 if len(columns) > 3 else 0, key="m_dims"
    )

  with col3:
    st.markdown("**Пример данных из файла**")
    st.caption(
        str(df[map_name].head(2).tolist()) if map_name else "Нет данных"
    )
    st.caption(
        str(df[map_price].head(2).tolist()) if map_price else "Нет данных"
    )
    st.caption(str(df[map_sku].head(2).tolist()) if map_sku else "Нет данных")
    st.caption(str(df[map_dims].head(2).tolist()) if map_dims else "Нет данных")

  st.divider()

  if st.button(
      "🚀 Проверить обязательные поля и сформировать файл для сайта",
      type="primary",
  ):
    errors = []
    if df[map_name].isnull().any():
      errors.append("В колонке 'Наименование товара' есть пустые ячейки!")
    if df[map_price].isnull().any():
      errors.append("В колонке 'Цена' есть пустые ячейки!")
    if df[map_dims].isnull().any():
      errors.append(
          "Внимание! Обязательное для сайта поле 'Габариты' имеет пустые"
          " значения в некоторых строках."
      )

    if errors:
      st.warning(
          "⚠️ Обнаружены проблемы, требующие внимания (карточки создадутся с"
          " предупреждениями для админки):"
      )
      for err in errors:
        st.write(f"- {err}")

    result_df = pd.DataFrame()
    result_df["product_title"] = df[map_name]
    result_df["product_price"] = df[map_price]
    result_df["product_sku"] = df[map_sku]
    result_df["attr_dimensions"] = df[map_dims]

    st.success("✅ Готово! Файл успешно отформатирован под требования сайта.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
      result_df.to_excel(writer, index=False, sheet_name="Import")

    st.download_button(
        label="📥 Скачать файл для загрузки на сайт",
        data=buffer.getvalue(),
        file_name="ready_for_site.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
else:
  st.info("👆 Загрузите файл прайс-листа или выгрузки выше, чтобы начать работу.")
