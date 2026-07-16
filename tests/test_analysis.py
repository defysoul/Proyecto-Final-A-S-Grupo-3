"""Pruebas del índice semántico sin descargar sentence-transformers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from sisav2_mcp.models.analysis import IniciativaSemantica
from sisav2_mcp.tools import analysis


class KeywordEncoder:
    """Encoder determinista pequeño para probar orden, caché y umbrales."""

    model_name = "tests/keyword-encoder-v1"

    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        vectors: list[list[float]] = []
        for text in texts:
            lowered = text.casefold()
            if "salud" in lowered:
                vectors.append([1.0, 0.1])
            elif "dato" in lowered:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.5, 0.5])
        return vectors


class NeverCalledEncoder(KeywordEncoder):
    """Falla si una caché válida intenta regenerar embeddings."""

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        raise AssertionError("La caché válida no debe volver a codificar documentos.")


def initiative(
    identifier: int,
    title: str,
    *,
    faculty: str | None = "Facultad de Salud",
    ods: list[str] | None = None,
    year: int | None = None,
) -> IniciativaSemantica:
    return IniciativaSemantica(
        idPostulacion=identifier,
        titulo=title,
        texto=title,
        facultad=faculty,
        ods=ods or [],
        anio=year,
    )


def detail_payload() -> dict[str, object]:
    return {
        "id": 3033,
        "nombre": "Título desde detalle",
        "formulario": {
            "formulario": [
                {
                    "posicion": 1,
                    "json": [
                        {
                            "name": "ESTANDAR_CORREO",
                            "label": "Correo",
                            "type": "email",
                            "value": "persona@utem.cl",
                        },
                        {
                            "name": "ENCARGADA",
                            "label": "Nombre Académico Responsable",
                            "type": "text",
                            "value": "Persona privada",
                        },
                        {
                            "name": "NOMBRE",
                            "label": "Nombre de la iniciativa",
                            "type": "text",
                            "value": "Taller de salud comunitaria",
                        },
                        {
                            "name": "uuid-objetivo",
                            "label": "Objetivos de la iniciativa",
                            "type": "textarea",
                            "value": "Fortalecer la promoción de salud.",
                        },
                        {
                            "name": "uuid-dominio",
                            "label": "Dominios disciplinarios",
                            "type": "checkbox-dependent",
                            "value": ["dominio-salud"],
                            "options": [
                                {
                                    "value": "dominio-salud",
                                    "label": "Salud pública",
                                    "selected": True,
                                },
                                {
                                    "value": "dominio-no",
                                    "label": "No seleccionado",
                                    "selected": False,
                                },
                            ],
                        },
                        {
                            "name": "uuid-ods",
                            "label": "ODS priorizados",
                            "type": "checkbox",
                            "value": ["ods-3"],
                            "options": [
                                {
                                    "value": "ods-3",
                                    "label": "ODS 3: Salud y bienestar",
                                    "selected": True,
                                },
                                {
                                    "value": "ods-4",
                                    "label": "ODS 4: Educación de calidad",
                                    "selected": False,
                                },
                            ],
                        },
                    ],
                }
            ]
        },
    }


def test_extract_dynamic_detail_keeps_relevant_text_and_excludes_pii() -> None:
    extracted = analysis.extraer_iniciativa_semantica(
        detail_payload(), modalidad="PRE_GRADO", facultad="Facultad de Salud"
    )

    assert extracted.id_postulacion == 3033
    assert extracted.titulo == "Taller de salud comunitaria"
    assert extracted.objetivos == ["Fortalecer la promoción de salud."]
    assert extracted.dominios == ["Salud pública"]
    assert extracted.ods == ["ODS 3"]
    assert "persona@utem.cl" not in extracted.texto
    assert "Persona privada" not in extracted.texto
    assert "No seleccionado" not in extracted.texto
    assert analysis.extraer_ods_de_detalle(detail_payload()) == ["ODS 3"]


def test_preparar_indice_uses_valid_local_cache(tmp_path: Path) -> None:
    cohort = [
        initiative(1, "Taller de salud comunitaria"),
        initiative(2, "Análisis de datos abiertos"),
    ]
    cache = tmp_path / "indice.json"
    first_encoder = KeywordEncoder()

    first_index, first_cached = analysis.preparar_indice_semantico(
        cohort, encoder=first_encoder, cache_path=cache
    )
    second_index, second_cached = analysis.preparar_indice_semantico(
        cohort, encoder=NeverCalledEncoder(), cache_path=cache
    )

    assert first_cached is False
    assert first_encoder.calls == 1
    assert second_cached is True
    assert first_index.metadatos.huella_cohorte == second_index.metadatos.huella_cohorte
    assert len(second_index.embeddings) == 2
    assert json.loads(cache.read_text(encoding="utf-8"))["metadatos"]["documentos"] == 2
    loaded = analysis.cargar_indice_cache(cache)
    assert loaded.metadatos.huella_cohorte == first_index.metadatos.huella_cohorte


def test_buscar_similares_excludes_source_and_orders_by_cosine() -> None:
    cohort = [
        initiative(1, "Taller de salud comunitaria"),
        initiative(2, "Capacitación de salud territorial"),
        initiative(3, "Laboratorio de datos abiertos"),
    ]

    result = analysis.buscar_iniciativas_similares(
        cohort, id_postulacion=1, encoder=KeywordEncoder(), limite=2
    )

    assert result["origen"]["idPostulacion"] == 1
    assert [item["idPostulacion"] for item in result["resultados"]] == [2, 3]
    assert result["resultados"][0]["similitud"] > result["resultados"][1]["similitud"]


def test_detectar_duplicados_returns_human_review_pairs() -> None:
    cohort = [
        initiative(1, "Taller de salud comunitaria"),
        initiative(2, "Capacitación de salud territorial"),
        initiative(3, "Laboratorio de datos abiertos"),
    ]

    result = analysis.detectar_duplicados(cohort, umbral=0.95, encoder=KeywordEncoder())

    assert result["paresEvaluados"] == 3
    assert len(result["duplicados"]) == 1
    pair = result["duplicados"][0]
    assert pair["izquierda"]["idPostulacion"] == 1
    assert pair["derecha"]["idPostulacion"] == 2
    assert "revisión humana" in result["nota"]


def test_ranking_ods_counts_an_initiative_once_per_faculty() -> None:
    cohort = [
        initiative(
            1,
            "Salud 1",
            faculty="Facultad A",
            ods=["ODS 3", "ODS 3"],
            year=2026,
        ),
        initiative(2, "Salud 2", faculty="Facultad A", ods=["ODS 3"], year=2026),
        initiative(
            3,
            "Datos",
            faculty="Facultad B",
            ods=["ODS 4: Educación"],
            year=2025,
        ),
        initiative(4, "Sin ODS", faculty="Facultad B", year=2026),
    ]

    result = analysis.ranking_facultades_por_ods(cohort)

    assert result["sinODS"] == 1
    assert result["ranking"][0] == {
        "ods": "ODS 3",
        "totalIniciativas": 2,
        "facultades": [
            {
                "facultad": "Facultad A",
                "totalIniciativas": 2,
                "idsPostulacion": [1, 2],
            }
        ],
    }
    assert analysis.ranking_ods(cohort, ods="4")["ranking"][0]["ods"] == "ODS 4"
    assert analysis.ranking_ods(cohort, anio=2025)["ranking"] == [
        {
            "ods": "ODS 4",
            "totalIniciativas": 1,
            "facultades": [
                {
                    "facultad": "Facultad B",
                    "totalIniciativas": 1,
                    "idsPostulacion": [3],
                }
            ],
        }
    ]


def test_cargar_cohorte_y_construir_indice_use_only_detail_gets(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.paths: list[str] = []

        async def get(self, path: str) -> dict[str, object]:
            self.paths.append(path)
            payload = detail_payload()
            payload["id"] = int(path.rsplit("/", maxsplit=1)[1])
            return payload

    async def scenario() -> tuple[analysis.SemanticIndex, bool, list[str]]:
        client = FakeClient()
        index, cached = await analysis.construir_indice_cohorte(
            client,  # type: ignore[arg-type]
            [
                {
                    "idPostulacion": 3033,
                    "modalidad": "PRE_GRADO",
                    "facultad": "Facultad de Salud",
                }
            ],
            encoder=KeywordEncoder(),
            cache_path=tmp_path / "cohorte.json",
        )
        return index, cached, client.paths

    index, cached, paths = asyncio.run(scenario())

    assert cached is False
    assert [item.id_postulacion for item in index.iniciativas] == [3033]
    assert paths == ["/convocatorias/postulacion/obtener/3033"]


def test_semantic_operations_validate_inputs() -> None:
    cohort = [initiative(1, "Taller de salud")]

    with pytest.raises(ValueError, match="exactamente uno"):
        analysis.buscar_iniciativas_similares(cohort, encoder=KeywordEncoder())
    with pytest.raises(ValueError, match="repetidos"):
        analysis.preparar_indice_semantico(cohort * 2, encoder=KeywordEncoder())
    with pytest.raises(ValueError, match="entre -1.0 y 1.0"):
        analysis.detectar_duplicados(cohort, umbral=1.1, encoder=KeywordEncoder())
