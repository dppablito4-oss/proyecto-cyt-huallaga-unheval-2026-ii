# Proyecto: Monitoreo y Evaluación de la Gestión del Recurso Hídrico en la Cuenca del Río Huallaga - Tingo María, Perú

Este proyecto de investigación aplicada tiene como objetivo implementar un sistema integral de monitoreo y evaluación de la gestión del recurso hídrico en la cuenca del río Huallaga, con énfasis en la identificación de fuentes de contaminación y la proposición de soluciones tecnológicas y de gestión sostenibles.

## 📋 Tabla de Contenidos

- [Resumen Ejecutivo](#-resumen-ejecutivo)
- [Justificación](#-justificación)
- [Objetivos](#-objetivos)
- [Metodología](#-metodología)
- [Resultados Esperados](#-resultados-esperados)
- [Impacto](#-impacto)
- [Equipo de Proyecto](#-equipo-de-proyecto)
- [Estado Actual](#-estado-actual-0)

## 📝 Resumen Ejecutivo

El proyecto aborda la problemática crítica de la contaminación del río Huallaga en la provincia de Leoncio Prado, Huánuco. Mediante una combinación de técnicas de **teledetección** (sensores remotos), **monitoreo in-situ** con sensores IoT y **análisis molecular** de ADN ambiental (eDNA), se busca identificar y caracterizar las principales fuentes de contaminación (agrícola, industrial, urbana) que amenazan el ecosistema y la salud humana.

## 💡 Justificación

La cuenca del río Huallaga es un ecosistema de gran biodiversidad y una fuente vital de agua para consumo humano, agricultura y generación hidroeléctrica. Sin embargo, enfrenta una creciente presión antropogénica que compromete su calidad ambiental y la salud de sus habitantes.

### Problemática Actual:
- **Erosión y sedimentación**: Debida a la deforestación y prácticas agrícolas inadecuadas.
- **Vertimiento de aguas residuales**: Falta de sistemas de tratamiento en centros urbanos.
- **Contaminación agrícola**: Uso intensivo de agroquímicos que llegan a los cuerpos de agua.
- **Minería ilegal**: Contaminación por mercurio y otros metales pesados en zonas afluentes.

La falta de datos en tiempo real y de bajo costo dificulta la toma de decisiones informadas por parte de las autoridades competentes (ANA, municipalidades, empresas de saneamiento).

## 🎯 Objetivos

### Objetivo General

Evaluar la calidad del recurso hídrico de la cuenca del río Huallaga mediante sistemas de monitoreo de bajo costo y análisis de eDNA, para identificar fuentes de contaminación y proponer alternativas de gestión sostenible.

### Objetivos Específicos

1. **Caracterización del ecosistema**: Identificar la diversidad de peces y macroinvertebrados bentónicos mediante análisis de eDNA.
2. **Monitoreo físico-químico**: Implementar sensores en puntos estratégicos (Tingo María, Castillo Grande, La Bella, etc.) para medir parámetros clave (pH, temperatura, OD, turbidez).
3. **Análisis espacial**: Utilizar imágenes satelitales (Landsat, Sentinel) para evaluar cambios en la cobertura vegetal y calidad del agua (turbidez, clorofila).
4. **Modelización y alerta temprana**: Desarrollar modelos hidrológicos para predecir patrones de flujo y calidad del agua.
5. **Propuesta de gestión**: Formular recomendaciones tecnológicas y normativas para la remediación y prevención de la contaminación.

## 🛠️ Metodología

### Fase 1: Diagnóstico y Selección de Puntos de Muestreo
- Revisión bibliográfica y cartográfica.
- Delimitación de la cuenca y subcuencas.
- selección de **10 puntos de muestreo** representativos:
    - Aguas arriba (zonas boscosas).
    - Puntos de vertimiento (desagües, acequias agrícolas).
    - Puntos de captación de agua para consumo.
    - Aguas abajo (zona de Tingo María).

### Fase 2: Monitoreo In-Situ (IoT)
**Tecnología**: Sensores de bajo costo (Grove, Atlas Scientific) conectados a ESP32/Raspberry Pi.
**Parámetros**: pH, temperatura, oxígeno disuelto (OD), conductividad, turbidez, potencial redox (ORP).
**Frecuencia**: Cada 15 minutos.
**Alimentación**: Paneles solares y baterías.

### Fase 3: Teledetección
**Satélites**: Landsat 8/9, Sentinel-2, Sentinel-3.
**Software**: QGIS, Google Earth Engine.
**Análisis**: Índices de vegetación (NDVI), turbidez, clorofila.

### Fase 4: Análisis Molecular (eDNA)
**Muestreo**: 1 L de agua por punto.
**Extracción**: Kits comerciales.
**PCR**: Reactivos específicos para peces y macroinvertebrados.
**Secuenciación**: Illumine NovaSeq/MiniSeq.
**Bioinformática**: QIIME2, Kraken2, MEGAN6.

### Fase 5: Integración y Modelización
**Plataforma**: Google Cloud Platform (BigQuery, Data Studio).
**Modelos**: Regresión múltiple, Series de tiempo (ARIMA), Machine Learning.

## 🎁 Resultados Esperados

1. **Mapa de riesgo de contaminación**: Detallando zonas vulnerables y fuentes de emisión.
2. **Base de datos en tiempo real**: Dashboard interactivo con datos de los sensores.
3. **Inventario de biodiversidad**: Listado taxonómico de especies acuáticas presentes.
4. **Informe técnico-científico**: Con análisis estadísticos y propuestas de mitigación.
5. **Modelo predictivo**: Para alerta temprana de eventos de contaminación.

## 🌎 Impacto

### Ambiental
- Mejora en la gestión de recursos hídricos.
- Protección de la biodiversidad acuática.
- Prevención de la contaminación de fuentes de agua.

### Social
- Mejora de la salud pública (agua más segura).
- Capacitación a comunidades locales en monitoreo ambiental.
- Concientización ciudadana.

### Económico
- Reducción de costos de monitoreo a largo plazo.
- Promoción del turismo sostenible (Río활동).
- Mejora de la competitividad agrícola (agua de mejor calidad).

## 👥 Equipo de Proyecto

| Rol | Nombre | Afiliación | Contacto |
| :--- | :--- | :--- | :--- |
| **Coordinador General** | [Nombre] | [Afiliación] | [Email] |
| **Investigador Principal** | [Nombre] | [Afiliación] | [Email] |
| **Especialista IoT** | [Nombre] | [Afiliación] | [Email] |
| **Biólogo Molecular** | [Nombre] | [Afiliación] | [Email] |
| **GIS Specialist** | [Nombre] | [Afiliación] | [Email] |
| **Asesoría Legal/Normativa** | [Nombre] | [Afiliación] | [Email] |

*(Nota: Los nombres deben ser completados con los integrantes reales del proyecto.)*

## 📊 Estado Actual (0)

El proyecto se encuentra en fase de **Conceptualización y Diseño**. Las actividades realizadas hasta la fecha son:

- [ ] Definición del problema y objetivos.
- [ ] Revisión bibliográfica preliminar.
- [ ] Selección de tecnología (sensores IoT, satélites).
- [ ] Propuesta inicial de puntos de muestreo.
- [ ] Contacto con instituciones aliadas (ANA, Municipalidad, UNHEVAL).

**Próximos pasos:**
- [ ] Obtener permisos de muestreo.
- [ ] Adquisición de equipos.
- [ ] Instalación del primer prototipo de sensor.

---

**Repositorio:** [Link al Repositorio](https://github.com/tu_usuario/proyecto-cyt-huallaga-unheval-2026-ii)
**Contacto:** [Correo de contacto]
**Financiador:** [Nombre de la entidad financiadora]

*Este documento es una plantilla y debe ser actualizado con los detalles específicos del proyecto en ejecución.*
