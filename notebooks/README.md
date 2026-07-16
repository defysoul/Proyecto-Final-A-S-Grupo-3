# Notebooks — experimentación (Foco 3)

`experimentos.ipynb` mide el aporte de cada componente de las tools de análisis
semántico: embeddings + coseno, semántico vs. keyword (TF-IDF), efecto de *k* y
umbral de duplicados. Está ejecutado (con outputs).

## Cómo correrlo

Dependencias de runtime ya vienen en el proyecto (`sentence-transformers`, que
arrastra `scikit-learn`, + `numpy`). Para abrirlo/ejecutarlo:

```powershell
uv run --with jupyter jupyter notebook notebooks/experimentos.ipynb
```

El primer uso descarga el modelo `paraphrase-multilingual-MiniLM-L12-v2` (~120 MB)
y requiere red.

## Nota sobre el corpus

El corpus es **ilustrativo**: objetivos de iniciativas VcM redactados a mano,
etiquetados por tema para poder medir precisión. La cohorte real se construye
desde SISAV2 en la demo (`sisav2-mcp index-demo`) y se excluye de git por PII. El
corpus golden del curso (2606/2648/2650 · 2690/2724/2788) llega como PDFs; aquí se
usan objetivos cortos para experimentos reproducibles sin datos personales.
