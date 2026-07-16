"""Modelo base para los DTOs de SISAV2.

Política de tolerancia (Spec / plan Paso 3): los campos no esenciales son
``Optional``; los campos desconocidos NO rompen el parseo — se conservan
(``extra="allow"``) y se loguean en ``DEBUG`` para detectar drift de la API.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger("sisav2_mcp.models")


class SisavModel(BaseModel):
    """Base tolerante: ignora-pero-conserva extras y los registra."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def _log_unknown_fields(self) -> SisavModel:
        extra = self.model_extra
        if extra:
            logger.debug(
                "%s: campos desconocidos conservados: %s",
                type(self).__name__,
                sorted(extra),
            )
        return self
