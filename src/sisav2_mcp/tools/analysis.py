"""Análisis semántico local y seguro de iniciativas SISAV2.

El módulo trabaja sobre una cohorte explícita de detalles ya autorizados. Antes
de generar embeddings reduce el form-builder dinámico de SISAV2 a texto útil
(título, objetivos, necesidad, dominios y ODS) y descarta campos de identidad.
No registra tools MCP ni ejecuta operaciones mutantes: ``register.py`` decide
cómo exponer estas funciones y quién construye la cohorte de la demo.

``sentence-transformers`` es una dependencia opcional. Se importa únicamente
al instanciar el encoder por defecto; las pruebas y cualquier integración pueden
inyectar un encoder compatible sin descargar un modelo.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import ValidationError

from ..models.analysis import (
    CacheIndiceSemantico,
    IniciativaSemantica,
    MetadatosIndiceSemantico,
    MiembroCohorte,
    ParDuplicado,
    ResultadoSimilar,
)
from ..models.detalle import CampoFormulario, DetalleIniciativa

if TYPE_CHECKING:
    from ..client import SisavClient


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_VERSION = 1
_DETAIL_PATH = "/convocatorias/postulacion/obtener"

_PII_FIELD_TOKENS = (
    "correo",
    "email",
    "mail",
    "encargad",
    "responsable",
    "rut",
    "telefono",
    "celular",
    "contacto",
    "nombre academico",
    "nombre docente",
)
_ODS_TOKENS = ("ods", "desarrollo sostenible")
_NEED_TOKENS = ("necesidad", "problema", "diagnost", "justific")
_DOMAIN_TOKENS = ("dominio", "disciplin")


class TextEncoder(Protocol):
    """Interfaz mínima para no acoplar el análisis a una librería concreta."""

    def encode(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Devuelve un embedding por cada texto recibido."""


class AnalysisDependencyError(RuntimeError):
    """La dependencia opcional necesaria para generar embeddings no está instalada."""


class SentenceTransformerEncoder:
    """Adaptador perezoso para el modelo multilingüe recomendado en el proyecto."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    @property
    def cache_key(self) -> str:
        """Identificador estable que invalida la caché si se cambia de modelo."""
        return self.model_name

    def _load_model(self) -> Any:
        try:
            module = importlib.import_module("sentence_transformers")
            factory = getattr(module, "SentenceTransformer")
        except (ImportError, AttributeError) as exc:
            raise AnalysisDependencyError(
                "El análisis semántico requiere la dependencia opcional "
                "'sentence-transformers'. Instálala para usar embeddings o "
                "inyecta un encoder compatible."
            ) from exc
        return factory(self.model_name)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is None:
            self._model = self._load_model()
        vectors = self._model.encode(
            list(texts), show_progress_bar=False, normalize_embeddings=True
        )
        return _coerce_matrix(vectors, expected_rows=len(texts))


@dataclass(frozen=True)
class SemanticIndex:
    """Índice vectorial pequeño, portable y serializable a JSON local."""

    iniciativas: tuple[IniciativaSemantica, ...]
    embeddings: tuple[tuple[float, ...], ...]
    metadatos: MetadatosIndiceSemantico

    @classmethod
    def from_cache(cls, cached: CacheIndiceSemantico) -> SemanticIndex:
        return _make_index(
            tuple(cached.iniciativas),
            tuple(tuple(vector) for vector in cached.embeddings),
            cached.metadatos,
        )

    def to_cache(self) -> CacheIndiceSemantico:
        return CacheIndiceSemantico(
            metadatos=self.metadatos,
            iniciativas=list(self.iniciativas),
            embeddings=[list(vector) for vector in self.embeddings],
        )


def extraer_iniciativa_semantica(
    detalle: DetalleIniciativa | Mapping[str, Any],
    *,
    modalidad: str | None = None,
    facultad: str | None = None,
    anio: int | None = None,
) -> IniciativaSemantica:
    """Extrae contenido analizable de un detalle de formulario heterogéneo.

    Se clasifica por ``name`` y ``label`` porque los identificadores de muchos
    campos son UUIDs que cambian según convocatoria. Los campos de correo,
    responsable y otros datos de contacto se ignoran incluso si su texto parece
    relevante. Para checkbox/radio se usan solo las opciones seleccionadas.
    """
    parsed = _as_detalle(detalle)
    titulo = _clean_text(parsed.nombre) or f"Iniciativa {parsed.id}"
    objetivos: list[str] = []
    necesidades: list[str] = []
    dominios: list[str] = []
    ods: list[str] = []

    for paso in parsed.formulario.formulario:
        for campo in paso.campos:
            descriptor = _descriptor_campo(campo)
            if _is_sensitive_field(descriptor):
                continue
            values = _selected_text_values(campo)
            if not values:
                continue

            if _is_title_field(campo, descriptor):
                titulo = values[0]
            elif _contains_any(descriptor, _ODS_TOKENS):
                ods.extend(_canonical_ods(value) for value in values)
            elif "objetiv" in descriptor:
                objetivos.extend(values)
            elif _contains_any(descriptor, _NEED_TOKENS):
                necesidades.extend(values)
            elif _contains_any(descriptor, _DOMAIN_TOKENS):
                dominios.extend(values)

    titulo = _clean_text(titulo) or f"Iniciativa {parsed.id}"
    objetivos = _unique_clean(objetivos)
    necesidades = _unique_clean(necesidades)
    dominios = _unique_clean(dominios)
    ods = _unique_clean(ods)
    texto = _join_unique([titulo, *objetivos, *necesidades, *dominios, *ods])

    return IniciativaSemantica(
        idPostulacion=parsed.id,
        titulo=titulo,
        texto=texto,
        modalidad=modalidad,
        facultad=facultad,
        anio=anio,
        objetivos=objetivos,
        necesidades=necesidades,
        dominios=dominios,
        ods=ods,
    )


def extraer_texto_analizable(
    detalle: DetalleIniciativa | Mapping[str, Any],
) -> str:
    """Devuelve el texto saneado que se entrega al encoder."""
    return extraer_iniciativa_semantica(detalle).texto


def extraer_ods_de_detalle(
    detalle: DetalleIniciativa | Mapping[str, Any],
) -> list[str]:
    """Devuelve los ODS seleccionados en un detalle dinámico, sin PII."""
    return extraer_iniciativa_semantica(detalle).ods


async def cargar_cohorte_desde_sisav(
    client: SisavClient,
    miembros: Sequence[MiembroCohorte | Mapping[str, Any]],
) -> list[IniciativaSemantica]:
    """Lee los detalles de una cohorte explícita y los convierte al DTO seguro.

    Esta es la pieza de integración para un preflight/CLI: los IDs vienen de un
    manifiesto local autorizado y cada llamada es un GET ya permitido por el
    cliente read-only. No incorpora ni persiste datos de identidad del detalle.
    """
    cohort = [_as_miembro(item) for item in miembros]
    _ensure_unique_ids(member.id_postulacion for member in cohort)
    iniciativas: list[IniciativaSemantica] = []
    for member in cohort:
        raw = await client.get(f"{_DETAIL_PATH}/{member.id_postulacion}")
        iniciativas.append(
            extraer_iniciativa_semantica(
                raw,
                modalidad=member.modalidad,
                facultad=member.facultad,
                anio=member.anio,
            )
        )
    return iniciativas


async def construir_indice_cohorte(
    client: SisavClient,
    miembros: Sequence[MiembroCohorte | Mapping[str, Any]],
    *,
    encoder: TextEncoder | None = None,
    cache_path: str | Path | None = None,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> tuple[SemanticIndex, bool]:
    """Carga una cohorte desde SISAV2 y construye/recupera su índice local.

    Retorna ``(indice, cache_utilizada)``. Es la API pública intencionalmente
    simple para el comando de preflight: recibe el ``SisavClient`` ya
    autenticado y el manifiesto local de IDs.
    """
    iniciativas = await cargar_cohorte_desde_sisav(client, miembros)
    return preparar_indice_semantico(
        iniciativas,
        encoder=encoder,
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
    )


def preparar_indice_semantico(
    iniciativas: Sequence[IniciativaSemantica | Mapping[str, Any]],
    *,
    encoder: TextEncoder | None = None,
    cache_path: str | Path | None = None,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> tuple[SemanticIndex, bool]:
    """Construye o reutiliza una caché válida para una cohorte saneada."""
    documents = tuple(_as_iniciativa(item) for item in iniciativas)
    _ensure_unique_ids(document.id_postulacion for document in documents)
    if ttl_seconds < 0:
        raise ValueError("ttl_seconds debe ser mayor o igual a cero.")

    resolved_encoder = encoder or SentenceTransformerEncoder()
    encoder_key = _encoder_key(resolved_encoder)
    fingerprint = _cohort_fingerprint(documents)
    path = Path(cache_path) if cache_path is not None else None

    if path is not None:
        cached = _load_cache(
            path,
            expected_fingerprint=fingerprint,
            expected_encoder=encoder_key,
            ttl_seconds=ttl_seconds,
        )
        if cached is not None:
            return cached, True

    index = _build_index(documents, resolved_encoder, fingerprint, encoder_key)
    if path is not None:
        _save_cache(path, index)
    return index, False


def cargar_indice_cache(path: str | Path) -> SemanticIndex:
    """Carga y valida un índice JSON ya generado, sin requerir el encoder.

    A diferencia de ``preparar_indice_semantico``, esta función no evalúa TTL,
    huella de cohorte ni nombre de modelo: sirve al servidor para reutilizar un
    índice que su preflight ya validó y construyó.
    """
    cache_path = Path(path)
    try:
        cached = CacheIndiceSemantico.model_validate_json(
            cache_path.read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise ValueError(f"No se pudo leer el índice semántico: {cache_path}") from exc
    except (ValidationError, ValueError) as exc:
        raise ValueError(
            f"El índice semántico no tiene un formato válido: {cache_path}"
        ) from exc
    try:
        return SemanticIndex.from_cache(cached)
    except ValueError as exc:
        raise ValueError(f"El índice semántico es inconsistente: {cache_path}") from exc


def buscar_iniciativas_similares(
    iniciativas: Sequence[IniciativaSemantica | Mapping[str, Any]],
    *,
    id_postulacion: int | None = None,
    consulta: str | None = None,
    limite: int = 5,
    similitud_minima: float = 0.0,
    encoder: TextEncoder | None = None,
    cache_path: str | Path | None = None,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    indice: SemanticIndex | None = None,
) -> dict[str, Any]:
    """Busca iniciativas parecidas a una postulación o a una consulta libre.

    Debe llegar exactamente uno de ``id_postulacion`` o ``consulta``. Si se
    consulta por ID, se reutiliza el vector ya indexado; la consulta libre se
    codifica con el mismo encoder del índice.
    """
    if (id_postulacion is None) == (consulta is None):
        raise ValueError("Indica exactamente uno de id_postulacion o consulta.")
    if limite <= 0:
        raise ValueError("limite debe ser mayor que cero.")
    _validate_similarity(similitud_minima, field="similitud_minima")

    documents = tuple(_as_iniciativa(item) for item in iniciativas)
    index, cache_used = _resolve_index(
        documents,
        indice=indice,
        encoder=encoder,
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
    )
    by_id = {
        document.id_postulacion: position
        for position, document in enumerate(index.iniciativas)
    }

    if id_postulacion is not None:
        position = by_id.get(id_postulacion)
        if position is None:
            raise ValueError(
                f"La postulación {id_postulacion} no pertenece a la cohorte semántica."
            )
        query_vector = index.embeddings[position]
        source: dict[str, Any] = {
            "idPostulacion": id_postulacion,
            "titulo": index.iniciativas[position].titulo,
        }
        exclude_id = id_postulacion
    else:
        query = _clean_text(consulta or "")
        if not query:
            raise ValueError("consulta no puede estar vacía.")
        resolved_encoder = encoder or SentenceTransformerEncoder()
        query_vector = _encode_one(resolved_encoder, query)
        source = {"consulta": query}
        exclude_id = None

    matches: list[tuple[float, IniciativaSemantica]] = []
    for document, vector in zip(index.iniciativas, index.embeddings, strict=True):
        if document.id_postulacion == exclude_id:
            continue
        score = _cosine(query_vector, vector)
        if score >= similitud_minima:
            matches.append((score, document))
    matches.sort(key=lambda item: (-item[0], item[1].id_postulacion))

    results = [
        _similar_result(document, score).model_dump(by_alias=True, exclude_none=True)
        for score, document in matches[:limite]
    ]
    return {
        "origen": source,
        "totalCohorte": len(index.iniciativas),
        "similitudMinima": similitud_minima,
        "cacheUtilizada": cache_used,
        "resultados": results,
    }


def detectar_duplicados(
    iniciativas: Sequence[IniciativaSemantica | Mapping[str, Any]],
    *,
    umbral: float = 0.84,
    limite: int | None = 20,
    encoder: TextEncoder | None = None,
    cache_path: str | Path | None = None,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    indice: SemanticIndex | None = None,
) -> dict[str, Any]:
    """Encuentra pares potencialmente duplicados por similitud coseno.

    El resultado es una alerta para revisión humana, no una decisión automática
    ni una modificación del estado de SISAV2.
    """
    _validate_similarity(umbral, field="umbral")
    if limite is not None and limite <= 0:
        raise ValueError("limite debe ser mayor que cero o None.")

    documents = tuple(_as_iniciativa(item) for item in iniciativas)
    index, cache_used = _resolve_index(
        documents,
        indice=indice,
        encoder=encoder,
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
    )
    pairs: list[ParDuplicado] = []
    for left_index, left_document in enumerate(index.iniciativas):
        for right_index in range(left_index + 1, len(index.iniciativas)):
            right_document = index.iniciativas[right_index]
            score = _cosine(index.embeddings[left_index], index.embeddings[right_index])
            if score >= umbral:
                pairs.append(
                    ParDuplicado(
                        izquierda=_similar_result(left_document, score),
                        derecha=_similar_result(right_document, score),
                        similitud=round(score, 4),
                    )
                )
    pairs.sort(
        key=lambda pair: (
            -pair.similitud,
            pair.izquierda.id_postulacion,
            pair.derecha.id_postulacion,
        )
    )
    if limite is not None:
        pairs = pairs[:limite]

    return {
        "umbral": umbral,
        "totalCohorte": len(index.iniciativas),
        "paresEvaluados": len(index.iniciativas) * (len(index.iniciativas) - 1) // 2,
        "cacheUtilizada": cache_used,
        "duplicados": [
            pair.model_dump(by_alias=True, exclude_none=True) for pair in pairs
        ],
        "nota": "Coincidencias para revisión humana; no se modifica SISAV2.",
    }


def ranking_facultades_por_ods(
    iniciativas: Sequence[IniciativaSemantica | Mapping[str, Any]],
    *,
    ods: str | None = None,
    anio: int | None = None,
    limite_ods: int | None = None,
    limite_facultades: int | None = 10,
) -> dict[str, Any]:
    """Agrupa iniciativas únicas por ODS y ranking de facultad dentro de cada ODS."""
    if limite_ods is not None and limite_ods <= 0:
        raise ValueError("limite_ods debe ser mayor que cero o None.")
    if limite_facultades is not None and limite_facultades <= 0:
        raise ValueError("limite_facultades debe ser mayor que cero o None.")

    documents = tuple(
        document
        for document in (_as_iniciativa(item) for item in iniciativas)
        if anio is None or document.anio == anio
    )
    requested_ods = _canonical_ods(ods) if ods is not None else None
    grouped: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    without_ods = 0
    for document in documents:
        document_ods = _unique_clean(document.ods)
        if not document_ods:
            without_ods += 1
            continue
        faculty = _clean_text(document.facultad or "") or "Sin facultad informada"
        for ods_name in document_ods:
            canonical = _canonical_ods(ods_name)
            if requested_ods is not None and canonical != requested_ods:
                continue
            grouped[canonical][faculty].add(document.id_postulacion)

    ranking: list[dict[str, Any]] = []
    for ods_name, faculties in grouped.items():
        sorted_faculties = sorted(
            faculties.items(), key=lambda item: (-len(item[1]), item[0].casefold())
        )
        if limite_facultades is not None:
            sorted_faculties = sorted_faculties[:limite_facultades]
        ranking.append(
            {
                "ods": ods_name,
                "totalIniciativas": len(set().union(*faculties.values())),
                "facultades": [
                    {
                        "facultad": faculty,
                        "totalIniciativas": len(ids),
                        "idsPostulacion": sorted(ids),
                    }
                    for faculty, ids in sorted_faculties
                ],
            }
        )
    ranking.sort(key=lambda item: (-item["totalIniciativas"], item["ods"]))
    if limite_ods is not None:
        ranking = ranking[:limite_ods]

    return {
        "filtroODS": requested_ods,
        "filtroAnio": anio,
        "totalCohorte": len(documents),
        "sinODS": without_ods,
        "ranking": ranking,
    }


def ranking_ods(
    iniciativas: Sequence[IniciativaSemantica | Mapping[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Alias corto y compatible para ``ranking_facultades_por_ods``."""
    return ranking_facultades_por_ods(iniciativas, **kwargs)


def _as_detalle(detalle: DetalleIniciativa | Mapping[str, Any]) -> DetalleIniciativa:
    if isinstance(detalle, DetalleIniciativa):
        return detalle
    return DetalleIniciativa.model_validate(detalle)


def _as_miembro(item: MiembroCohorte | Mapping[str, Any]) -> MiembroCohorte:
    if isinstance(item, MiembroCohorte):
        return item
    return MiembroCohorte.model_validate(item)


def _as_iniciativa(
    item: IniciativaSemantica | Mapping[str, Any],
) -> IniciativaSemantica:
    if isinstance(item, IniciativaSemantica):
        return item
    return IniciativaSemantica.model_validate(item)


def _descriptor_campo(campo: CampoFormulario) -> str:
    return _normalise(f"{campo.name} {campo.label or ''}")


def _is_sensitive_field(descriptor: str) -> bool:
    return _contains_any(descriptor, _PII_FIELD_TOKENS)


def _is_title_field(campo: CampoFormulario, descriptor: str) -> bool:
    name = _normalise(campo.name)
    if name in {"nombre", "titulo", "titulo iniciativa"}:
        return True
    return "nombre" in descriptor and "iniciativa" in descriptor


def _selected_text_values(campo: CampoFormulario) -> list[str]:
    """Extrae texto de un campo sin convertir opciones no seleccionadas en corpus."""
    selected_options = _selected_option_labels(campo.value, campo.options)
    if selected_options:
        return selected_options
    return _plain_text_values(campo.value)


def _selected_option_labels(value: Any, options: list[Any] | None) -> list[str]:
    if not options:
        return []
    selected_values = {str(item) for item in _flatten_values(value)}
    labels: list[str] = []
    for option in options:
        if not isinstance(option, Mapping):
            continue
        option_value = option.get("value")
        selected = bool(option.get("selected"))
        if selected or (
            option_value is not None and str(option_value) in selected_values
        ):
            label = option.get("label")
            if isinstance(label, str):
                labels.append(label)
    return _unique_clean(labels)


def _plain_text_values(value: Any) -> list[str]:
    values: list[str] = []
    for item in _flatten_values(value):
        if isinstance(item, str) and not _looks_like_identifier(item):
            values.append(item)
        elif isinstance(item, Mapping):
            for key in ("label", "nombre", "texto", "descripcion"):
                candidate = item.get(key)
                if isinstance(candidate, str):
                    values.append(candidate)
                    break
    return _unique_clean(values)


def _flatten_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, int, float, bool, Mapping)):
        return [value]
    if isinstance(value, Sequence):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(_flatten_values(item))
        return flattened
    return []


def _looks_like_identifier(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            value.strip().casefold(),
        )
    )


def _canonical_ods(value: str) -> str:
    cleaned = _clean_text(value)
    normalized = _normalise(cleaned)
    match = re.search(
        r"(?:ods|objetivos? de desarrollo sostenible)?\s*#?\s*(\d{1,2})\b",
        normalized,
    )
    if match is not None:
        return f"ODS {int(match.group(1))}"
    if normalized.startswith("ods "):
        return cleaned
    return cleaned


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents.casefold()).strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _unique_clean(values: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        key = _normalise(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
    return unique


def _join_unique(values: Sequence[str]) -> str:
    return "\n".join(_unique_clean(values))


def _contains_any(value: str, tokens: Sequence[str]) -> bool:
    return any(token in value for token in tokens)


def _cohort_fingerprint(documents: Sequence[IniciativaSemantica]) -> str:
    canonical = [
        document.model_dump(mode="json", by_alias=True, exclude_none=True)
        for document in sorted(documents, key=lambda item: item.id_postulacion)
    ]
    serialized = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _encoder_key(encoder: TextEncoder) -> str:
    for attribute in ("cache_key", "model_name"):
        value = getattr(encoder, attribute, None)
        if isinstance(value, str) and value:
            return value
    encoder_type = type(encoder)
    return f"{encoder_type.__module__}.{encoder_type.__qualname__}"


def _build_index(
    documents: tuple[IniciativaSemantica, ...],
    encoder: TextEncoder,
    fingerprint: str,
    encoder_key: str,
) -> SemanticIndex:
    if documents:
        texts = [document.texto for document in documents]
        embeddings = tuple(
            _normalise_vector(vector) for vector in _encode(encoder, texts)
        )
        dimension = len(embeddings[0])
    else:
        embeddings = ()
        dimension = 0
    metadata = MetadatosIndiceSemantico(
        version=_CACHE_VERSION,
        creado_en=datetime.now(UTC),
        huella_cohorte=fingerprint,
        encoder=encoder_key,
        documentos=len(documents),
        dimension=dimension,
    )
    return _make_index(documents, embeddings, metadata)


def _make_index(
    documents: tuple[IniciativaSemantica, ...],
    embeddings: tuple[tuple[float, ...], ...],
    metadata: MetadatosIndiceSemantico,
) -> SemanticIndex:
    _ensure_unique_ids(document.id_postulacion for document in documents)
    if len(documents) != len(embeddings):
        raise ValueError(
            "El índice tiene una cantidad distinta de documentos y embeddings."
        )
    if metadata.documentos != len(documents):
        raise ValueError("Los metadatos del índice no coinciden con la cohorte.")
    dimensions = {len(vector) for vector in embeddings}
    if len(dimensions) > 1:
        raise ValueError("Los embeddings del índice no tienen una dimensión uniforme.")
    dimension = next(iter(dimensions), 0)
    if metadata.dimension != dimension:
        raise ValueError("La dimensión declarada no coincide con los embeddings.")
    if metadata.version != _CACHE_VERSION:
        raise ValueError("La versión de caché del índice no es compatible.")
    normalised = tuple(_normalise_vector(vector) for vector in embeddings)
    return SemanticIndex(documents, normalised, metadata)


def _resolve_index(
    documents: tuple[IniciativaSemantica, ...],
    *,
    indice: SemanticIndex | None,
    encoder: TextEncoder | None,
    cache_path: str | Path | None,
    ttl_seconds: int,
) -> tuple[SemanticIndex, bool]:
    _ensure_unique_ids(document.id_postulacion for document in documents)
    if indice is not None:
        fingerprint = _cohort_fingerprint(documents)
        if indice.metadatos.huella_cohorte != fingerprint:
            raise ValueError(
                "El índice proporcionado no corresponde a la cohorte recibida."
            )
        return indice, True
    return preparar_indice_semantico(
        documents,
        encoder=encoder,
        cache_path=cache_path,
        ttl_seconds=ttl_seconds,
    )


def _load_cache(
    path: Path,
    *,
    expected_fingerprint: str,
    expected_encoder: str,
    ttl_seconds: int,
) -> SemanticIndex | None:
    try:
        cached = CacheIndiceSemantico.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, ValueError):
        return None
    metadata = cached.metadatos
    created_at = metadata.creado_en
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age = datetime.now(UTC) - created_at.astimezone(UTC)
    if (
        metadata.version != _CACHE_VERSION
        or metadata.huella_cohorte != expected_fingerprint
        or metadata.encoder != expected_encoder
        or age > timedelta(seconds=ttl_seconds)
    ):
        return None
    try:
        return SemanticIndex.from_cache(cached)
    except ValueError:
        return None


def _save_cache(path: Path, index: SemanticIndex) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            index.to_cache().model_dump_json(indent=2), encoding="utf-8"
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _encode(encoder: TextEncoder, texts: Sequence[str]) -> list[list[float]]:
    return _coerce_matrix(encoder.encode(texts), expected_rows=len(texts))


def _encode_one(encoder: TextEncoder, text: str) -> tuple[float, ...]:
    vectors = _encode(encoder, [text])
    return _normalise_vector(vectors[0])


def _coerce_matrix(raw: Any, *, expected_rows: int) -> list[list[float]]:
    try:
        rows = list(raw)
    except TypeError as exc:
        raise ValueError(
            "El encoder no devolvió una matriz iterable de embeddings."
        ) from exc
    if len(rows) != expected_rows:
        raise ValueError(
            f"El encoder devolvió {len(rows)} embeddings para {expected_rows} textos."
        )
    return [_coerce_vector(row) for row in rows]


def _coerce_vector(raw: Any) -> list[float]:
    if isinstance(raw, (str, bytes)):
        raise ValueError("Un embedding debe ser una secuencia numérica, no texto.")
    try:
        values = [float(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError("El encoder devolvió un embedding no numérico.") from exc
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("El encoder devolvió un embedding vacío o no finito.")
    return values


def _normalise_vector(vector: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in vector)
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("El encoder devolvió un embedding de norma cero.")
    return tuple(value / norm for value in values)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("No se pueden comparar embeddings de distinta dimensión.")
    return sum(a * b for a, b in zip(left, right, strict=True))


def _similar_result(document: IniciativaSemantica, score: float) -> ResultadoSimilar:
    return ResultadoSimilar(
        idPostulacion=document.id_postulacion,
        titulo=document.titulo,
        similitud=round(score, 4),
        modalidad=document.modalidad,
        facultad=document.facultad,
        ods=document.ods,
        dominios=document.dominios,
    )


def _validate_similarity(value: float, *, field: str) -> None:
    if not -1.0 <= value <= 1.0:
        raise ValueError(f"{field} debe estar entre -1.0 y 1.0.")


def _ensure_unique_ids(ids: Sequence[int] | Any) -> None:
    values = list(ids)
    if len(values) != len(set(values)):
        raise ValueError("La cohorte contiene idPostulacion repetidos.")
