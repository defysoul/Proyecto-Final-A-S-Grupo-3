"""Backend SISAV2 *simulado* en memoria para el commit de la demo.

Cierra el patrón dry-run -> commit sin tocar SISAV2 real: el ``would_request``
que la capa de previews (:mod:`sisav2_mcp.tools.writes`) deja preparado se
"aplica" contra un diccionario en memoria y se relee (read-back). Este módulo
**no tiene cliente HTTP**: por construcción, un commit jamás llega al sistema
institucional. La única forma de mutar SISAV2 real sigue siendo inexistente en
el código.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .audit import AuditLog
from .models.writes import CommitResult, PermisoEvaluado

# Campos de identidad de entidad que, si vienen en el body, fijan a qué registro
# se aplica la operación (permite actualizar/accionar sobre el mismo objeto).
_CAMPOS_ID = ("idPostulacion", "idProyecto", "idOrigen", "id")


class CommitNoHabilitado(RuntimeError):
    """Se pidió ``confirmar`` pero no hay backend mock activo para aplicar."""


class MockSisav2Backend:
    """Almacén en memoria que aplica un ``would_request`` y lo relee."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._contador = 1000

    def _clave(self, body: dict[str, Any]) -> str:
        for campo in _CAMPOS_ID:
            valor = body.get(campo)
            if valor is not None:
                return f"{campo}:{valor}"
        self._contador += 1
        return f"mock:{self._contador}"

    def aplicar(
        self, operacion: str, would_request: dict[str, Any], *, request_id: str
    ) -> tuple[str, dict[str, Any]]:
        """Aplica la solicitud hipotética al store y devuelve (id, read_back)."""
        body = dict(would_request.get("body", {}))
        clave = self._clave(body)
        registro = self._store.get(clave) or {"entidad_id": clave, "historial": []}
        registro["operacion"] = operacion
        registro["ultima_operacion"] = operacion
        registro["ultimo_request_id"] = request_id
        registro["metodo"] = would_request.get("method")
        registro["path"] = would_request.get("path")
        registro["body"] = body
        registro.setdefault("historial", []).append(
            {"operacion": operacion, "request_id": request_id}
        )
        self._store[clave] = registro
        return clave, dict(registro)

    def leer(self, entidad_id: str) -> dict[str, Any]:
        """Read-back: relee el registro tal cual quedó almacenado."""
        return dict(self._store[entidad_id])


def aplicar_commit(
    preview: dict[str, Any],
    *,
    backend: MockSisav2Backend,
    actor: str,
    request_id: str,
    audit: AuditLog | None = None,
) -> dict[str, Any]:
    """Aplica un preview dry-run contra el mock y devuelve un ``CommitResult``."""
    operacion = str(preview["operacion"])
    entidad_id, read_back = backend.aplicar(
        operacion, preview["would_request"], request_id=request_id
    )
    resultado = CommitResult(
        operacion=operacion,
        permiso=PermisoEvaluado.model_validate(preview["permiso"]),
        request_id=request_id,
        entidad_id=str(entidad_id),
        diff=dict(preview.get("diff", {})),
        efecto_aplicado=(
            f"APLICADO EN MOCK: {preview.get('efecto_previsto', '')}".strip()
        ),
        read_back=read_back,
    )
    if audit is not None:
        audit.append(
            {
                "actor": actor,
                "operacion": operacion,
                "request_id": request_id,
                "entidad_id": str(entidad_id),
                "aplicado": True,
                "backend": "mock",
            }
        )
    return resultado.model_dump(mode="json")


def exigir_backend(
    backend: MockSisav2Backend | None, *, confirmar: bool
) -> MockSisav2Backend | None:
    """Resuelve el backend a usar; protege el commit real (inexistente).

    Sin ``confirmar`` no se necesita backend (dry-run). Con ``confirmar`` pero
    sin backend mock, se rechaza: nunca hay un camino para mutar SISAV2 real.
    """
    if not confirmar:
        return None
    if backend is None:
        raise CommitNoHabilitado(
            "El commit real no está habilitado: usa dry-run (por defecto), o "
            "activa el simulador con SISAV2_MOCK_WRITES=1 para un commit contra mock."
        )
    return backend


def finalizar_escritura(
    preview: dict[str, Any],
    *,
    confirmar: bool,
    backend: MockSisav2Backend | None,
    actor: str,
    audit: AuditLog | None = None,
) -> dict[str, Any]:
    """Devuelve el preview (dry-run) o el ``CommitResult`` según ``confirmar``."""
    backend = exigir_backend(backend, confirmar=confirmar)
    if backend is None:
        return preview
    return aplicar_commit(
        preview,
        backend=backend,
        actor=actor,
        request_id=uuid4().hex,
        audit=audit,
    )
