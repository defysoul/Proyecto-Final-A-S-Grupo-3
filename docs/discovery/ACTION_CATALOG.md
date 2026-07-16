# Catálogo de acciones — analista VcM → endpoint → tool (Fase 1)

> Puente explícito hacia el Spec 2. Una fila por acción que hace hoy el analista.
> Fecha: 2026-06-07.

| Acción del analista | Endpoint(s) | Tool propuesta (Fase 1) | Tipo | Estado |
|---------------------|-------------|--------------------------|------|--------|
| Resolver identidad/permisos | `GET /usuarios/verifica-token` | (interno auth) | lectura | v1 |
| Listar/filtrar postulaciones | `GET /convocatorias/postulacion/buscar` (`estado[]`,`ingreso`,`modalidad`,`offset`,`limit`,`ordenamiento`,`idUsuario`,`roles[]`) | `listar_postulaciones` | lectura | v1 |
| Indicadores por estado | `GET /convocatorias/postulacion/totales/{idUsuario}?modalidad=` | `resumen_indicadores` | lectura | v1 |
| Ver detalle de iniciativa (7 pasos) | `GET /convocatorias/postulacion/obtener/{id}` | `obtener_detalle_iniciativa` | lectura | v1 |
| Ver fases/plantilla de la postulación | `GET /convocatorias/fases/obtener/{idFase}` | (parte de detalle) | lectura | v1 |
| Consultar admisibilidad | `GET /convocatorias/postulacion/buscar` (`estado=[3,6,2,4]`,`ingreso=false`) | `listar_postulaciones`/`consultar_admisibilidad` | lectura | v1 |
| Ver evaluación de admisibilidad | _(sin endpoint propio: reutiliza `obtener/{id}` + `fases/obtener/{idFase}`)_ | (parte de `obtener_detalle_iniciativa`) | lectura | v1 |
| Ver bitácora | `GET /convocatorias/postulacion/listar-cambios?idPostulacion=&offset=&limit=` | `ver_bitacora` | lectura | v1 |
| Ver planificación / cambio de fase | `GET /convocatorias/postulacion/buscar` (Planif. `estado=[5]`; Cambio Fase `estado=[todos]`, `ingreso=false`) | `listar_postulaciones` | lectura | v1 |
| Ver ejecución y seguimiento | `GET /proyectos/listar` (`offset`,`limit`,`idUsuario`,`searchTerm`,`ordenamiento`,`modalidad`) | `listar_proyectos` | lectura | v1 |
| Ver repositorios | `GET /mantenedores/repositorios?vista=REPOSITORIO_VCM&roles={csv}` | `listar_repositorios` | lectura | v1 |
| Avance Global (KPIs) | `GET /proyectos/estadisticas/globales-proyectos` | `avance_global` | lectura | v1 |
| Avance Global (grilla) | `GET /proyectos/estadisticas/proyectos?offset=&limit=` (**400 server-side**, ver inventario) | `avance_global` | lectura | **diferido Fase 1** |
| Exportar postulaciones a Excel | `POST /convocatorias/postulacion/exportar-excel` (body JSON; devuelve URL S3 prefirmada a XLSX) | `exportar_postulaciones` | lectura (POST) | v1 (URL) / v2 (parseo) |
| Catálogo convocatorias | `GET /convocatorias/listar-combo` | Resource `sisav2://catalogo/convocatorias` | lectura | v1 |
| Catálogo carreras | `GET /mantenedores/listarCarrera[?facultadId=]` | Resource `sisav2://catalogo/carreras` | lectura | v1 |
| Catálogo facultades | `GET /mantenedores/listarFacultad` | Resource `sisav2://catalogo/facultades` | lectura | v1 |
| Catálogo estados | `GET /convocatorias/estado/buscar` | Resource `sisav2://catalogo/estados` | lectura | v1 |
| _Crear postulación_ | | _(v2)_ | escritura | diferido v2 |
| _Evaluar admisibilidad (Admisible/Reformular/Rechazar)_ | | _(v2)_ | escritura | diferido v2 |
| _Dejar feedback en bitácora_ | | _(v2)_ | escritura | diferido v2 |
| _Cambio de fase_ | | _(v2)_ | escritura | diferido v2 |

> Las filas en _cursiva_ son escrituras: se registran aquí si aparecen en el recon, pero **no se
> ejecutan** en Fase 0 ni se implementan en v1.

**Notas para Fase 1 (de la sesión 2026-06-08):**
- **Ejecución y Seguimiento** usa un endpoint distinto (`GET /proyectos/listar`, clave raíz `data`,
  con `id` de proyecto ≠ `idpostulacion`) → tool propia `listar_proyectos`, NO `listar_postulaciones`.
- **Exportar a Excel** es `POST` pero de **solo lectura** (genera un reporte): el cliente GET-only
  necesita una **excepción en allowlist**. Devuelve URL prefirmada de S3 a un XLSX (no datos JSON);
  v1 puede exponer la URL, el parseo del XLSX se difiere a v2.
- **Avance Global (grilla)** devuelve 400 server-side incluso con la request exacta del SPA → diferido.
- Resources de catálogo confirmados con shape: convocatorias, carreras, facultades, **estados**, fases.
