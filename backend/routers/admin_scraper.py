"""
admin_scraper.py

Router administrativo para cargar la serie histórica de la Canasta Básica
de Crianza publicada por el INDEC (archivo .xlsx) y normalizarla al formato
que consume el módulo de Liquidaciones.

Endpoint:
    POST /api/admin/upload-indec

Notas de implementación:
- El INDEC suele publicar estos Excel con varias filas de metadata/encabezado
  "sucio" antes de la fila real de columnas (títulos del organismo, notas al
  pie, fecha de publicación, etc.). Por eso NO asumimos que la fila 0 es el
  header: buscamos la fila que contiene 'Período' y a partir de ahí leemos.
- Este router es solo lectura/transformación. El upsert a Supabase está
  dejado como lógica comentada para que la conectes con tu cliente real
  (service_role key, nunca la anon key, para un endpoint admin).
"""

import io
import logging
import re
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

logger = logging.getLogger("admin_scraper")

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Config: nombres de columnas esperados en el Excel del INDEC y su mapeo
# al identificador de "tramo" que usa liquidaciones.js
# ---------------------------------------------------------------------------
COLUMNA_PERIODO = "Período"

MAPEO_TRAMOS: dict[str, str] = {
    "< 1 año": "menor_1_anio",
    "1 a 3 años": "1_a_3",
    "4 a 5 años": "4_a_5",
    "6 a 12 años": "6_a_12",
}

EXTENSIONES_PERMITIDAS = (".xlsx",)


# ---------------------------------------------------------------------------
# Modelos de respuesta
# ---------------------------------------------------------------------------
class RegistroCanasta(BaseModel):
    periodo: str   # formato "YYYY-MM"
    tramo: str     # menor_1_anio | 1_a_3 | 4_a_5 | 6_a_12
    valor: float


class UploadIndecResponse(BaseModel):
    filas_procesadas: int
    periodos_detectados: int
    registros: list[RegistroCanasta]
    advertencias: list[str] = []


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------
def _validar_extension(filename: str | None) -> None:
    if not filename or not filename.lower().endswith(EXTENSIONES_PERMITIDAS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un Excel .xlsx (formato publicado por INDEC).",
        )


def _leer_excel_crudo(contenido: bytes) -> pd.DataFrame:
    """
    Lee el Excel sin asumir header, para poder ubicar manualmente la fila
    donde arrancan las columnas reales (el INDEC agrega filas de título
    antes de la tabla de datos).
    """
    try:
        return pd.read_excel(
            io.BytesIO(contenido),
            header=None,
            engine="openpyxl",
        )
    except ValueError as exc:
        # pandas/openpyxl lanzan ValueError si el binario no es un xlsx válido
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo leer el archivo como Excel válido: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - lo traducimos a un 400 legible
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error inesperado al abrir el archivo: {exc}",
        ) from exc


def _encontrar_fila_header(df_crudo: pd.DataFrame) -> int:
    """
    Busca la fila que contiene 'Período' en alguna celda: esa es la fila
    de encabezados reales. Recorremos solo las primeras 20 filas, que es
    más que suficiente margen para el bloque de metadata del INDEC.
    """
    limite = min(20, len(df_crudo))
    for idx in range(limite):
        fila = df_crudo.iloc[idx].astype(str).str.strip()
        if fila.str.contains(COLUMNA_PERIODO, case=False, na=False).any():
            return idx

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"No se encontró la columna '{COLUMNA_PERIODO}' en las primeras "
            f"{limite} filas del archivo. Verificá que sea la planilla "
            "oficial de Canasta Básica de Crianza del INDEC."
        ),
    )


def _normalizar_periodo(valor: Any) -> str | None:
    """
    Convierte distintos formatos en que el INDEC puede publicar el período
    ('ene-20', 'enero 2020', '2020-01', datetime, etc.) a 'YYYY-MM'.
    Devuelve None si no pudo interpretarlo (la fila se descarta con warning).
    """
    if pd.isna(valor):
        return None

    # Caso 1: ya viene como datetime/Timestamp (pandas suele parsear así)
    if isinstance(valor, (pd.Timestamp, datetime)):
        return f"{valor.year:04d}-{valor.month:02d}"

    texto = str(valor).strip().lower()

    # Caso 2: formato "2020-01" o "2020/01"
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", texto)
    if m:
        anio, mes = int(m.group(1)), int(m.group(2))
        return f"{anio:04d}-{mes:02d}"

    # Caso 3: abreviaturas en español "ene-20", "ene-2020", "enero 2020"
    meses_es = {
        "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
        "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    }
    m = re.match(r"^([a-záéíóú]{3,})[\s\-/]+(\d{2,4})$", texto)
    if m:
        mes_txt, anio_txt = m.group(1)[:3], m.group(2)
        mes = meses_es.get(mes_txt)
        if mes:
            anio = int(anio_txt)
            if anio < 100:  # "ene-20" -> 2020
                anio += 2000
            return f"{anio:04d}-{mes:02d}"

    return None


def _parsear_valor_numerico(valor: Any) -> float | None:
    """Convierte el valor de la celda a float, tolerando separadores '.'/',' """
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto = texto.replace(".", "").replace(",", ".")  # 545.683,00 -> 545683.00
    try:
        return float(texto)
    except ValueError:
        return None


def _procesar_dataframe(df_crudo: pd.DataFrame) -> tuple[list[RegistroCanasta], list[str]]:
    fila_header = _encontrar_fila_header(df_crudo)

    df = df_crudo.iloc[fila_header + 1:].copy()
    df.columns = df_crudo.iloc[fila_header].astype(str).str.strip()
    df = df.reset_index(drop=True)

    columnas_tramo = list(MAPEO_TRAMOS.keys())
    faltantes = [c for c in [COLUMNA_PERIODO, *columnas_tramo] if c not in df.columns]
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Faltan columnas esperadas en el archivo: "
                f"{', '.join(faltantes)}. Columnas encontradas: {list(df.columns)}"
            ),
        )

    registros: list[RegistroCanasta] = []
    advertencias: list[str] = []

    for i, fila in df.iterrows():
        periodo = _normalizar_periodo(fila[COLUMNA_PERIODO])
        if periodo is None:
            # Filas de notas al pie, totales, o separadores en blanco al final
            # de la planilla suelen caer acá; las salteamos sin frenar todo.
            continue

        for columna_indec, tramo_id in MAPEO_TRAMOS.items():
            valor = _parsear_valor_numerico(fila[columna_indec])
            if valor is None:
                advertencias.append(
                    f"Fila {i + fila_header + 2}: valor no numérico para "
                    f"'{columna_indec}' en período {periodo}, se omitió."
                )
                continue

            registros.append(
                RegistroCanasta(periodo=periodo, tramo=tramo_id, valor=valor)
            )

    if not registros:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo se leyó correctamente pero no se pudo extraer ningún registro válido.",
        )

    return registros, advertencias


# ---------------------------------------------------------------------------
# Upsert a Supabase (LÓGICA SIMULADA / COMENTADA)
# ---------------------------------------------------------------------------
def _upsert_supabase_simulado(registros: list[RegistroCanasta]) -> None:
    """
    Placeholder documentado de cómo se haría el upsert real.

    Requisitos para activarlo:
      - Tabla en Supabase, ej:
            create table canasta_basica_crianza (
                id         bigint generated always as identity primary key,
                periodo    text not null,          -- 'YYYY-MM'
                tramo      text not null,           -- menor_1_anio | 1_a_3 | 4_a_5 | 6_a_12
                valor      numeric(12,2) not null,
                updated_at timestamptz not null default now(),
                unique (periodo, tramo)
            );
      - Cliente inicializado con la SERVICE_ROLE key (este es un endpoint
        admin que escribe datos maestros; nunca uses la anon key acá).

    from supabase import create_client
    import os

    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    payload = [
        {"periodo": r.periodo, "tramo": r.tramo, "valor": r.valor}
        for r in registros
    ]

    # Supabase-py expone upsert() sobre la tabla; on_conflict apunta al
    # constraint único (periodo, tramo) para que reemplace en vez de duplicar.
    respuesta = (
        supabase.table("canasta_basica_crianza")
        .upsert(payload, on_conflict="periodo,tramo")
        .execute()
    )

    if getattr(respuesta, "data", None) is None:
        raise RuntimeError(f"Upsert a Supabase no devolvió datos: {respuesta}")

    # Para volúmenes grandes (varios años x 4 tramos), conviene trocear
    # el payload en lotes de ~500 filas para no exceder límites de la API:
    #
    # LOTE = 500
    # for i in range(0, len(payload), LOTE):
    #     supabase.table("canasta_basica_crianza") \\
    #         .upsert(payload[i:i + LOTE], on_conflict="periodo,tramo") \\
    #         .execute()
    """
    # Sin implementación real todavía: solo logueamos para dejar trazabilidad
    # mientras el endpoint se prueba en desarrollo.
    logger.info(
        "[admin_scraper] (simulado) upsert de %d registros a Supabase "
        "en tabla canasta_basica_crianza (on_conflict=periodo,tramo)",
        len(registros),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/upload-indec", response_model=UploadIndecResponse)
async def upload_indec(file: UploadFile = File(...)) -> UploadIndecResponse:
    """
    Recibe el Excel oficial de Canasta Básica de Crianza del INDEC,
    lo normaliza y (simuladamente) lo upsertea en Supabase.

    Respuestas de error:
      400 - archivo con extensión inválida, formato ilegible, columnas
            faltantes o sin registros procesables.
      413 - archivo vacío.
      500 - error no esperado durante el procesamiento.
    """
    _validar_extension(file.filename)

    contenido = await file.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo llegó vacío.",
        )

    try:
        df_crudo = _leer_excel_crudo(contenido)
        registros, advertencias = _procesar_dataframe(df_crudo)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado procesando el Excel de INDEC")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al procesar el archivo: {exc}",
        ) from exc

    try:
        _upsert_supabase_simulado(registros)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error al hacer upsert en Supabase")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Los datos se procesaron pero falló el guardado en base: {exc}",
        ) from exc

    periodos_detectados = len({r.periodo for r in registros})

    return UploadIndecResponse(
        filas_procesadas=len(registros),
        periodos_detectados=periodos_detectados,
        registros=registros,
        advertencias=advertencias,
    )
