# Referencia de notación ArchiMate 3.2 (para el canvas)

Síntesis del *Mastering ArchiMate Edition 3.2* (Gerben Wierda), sección "ArchiMate Basics"
(el excerpt en [`defs/`](../defs/MasteringArchiMateEdition3.2-Screen-Excerpt-20241025-O.pdf)).
Es la fuente de verdad para los **custom nodes/edges** del editor canvas (SPEC §8.2) y para
extender el `registry` cuando sumemos tipos más allá del subconjunto v1 (§4.2).

> ArchiMate es **color-neutral**: el color no tiene significado formal. ArqHub colorea **por capa**
> (el esquema de la mayoría de las herramientas y el elegido por la SPEC §8.2), no por aspecto como
> hace el libro. La forma/ícono del elemento es lo que distingue el tipo dentro de una capa.

## Estructura del metamodelo: capas × aspectos

Un elemento se ubica en una **capa** (fila) y un **aspecto** (columna). El aspecto define el rol
gramatical (sujeto-verbo-objeto); la capa define el nivel de abstracción.

**Aspectos (columnas):**
- **Active Structure** — el "quién": sujetos capaces de ejecutar comportamiento.
- **Behavior** — el "qué hace": el comportamiento en sí.
- **Passive Structure** — el "sobre qué": objetos sobre los que se actúa.
- **Motivation** — el "por qué" (aspecto transversal aparte).

Regla base: *Active structure* `Assigned-To` *Behavior*; *Behavior* `Access` *Passive structure*.

**Capas (filas) y color en ArqHub:**

| Capa | Color ArqHub | Aspecto activo / comportamiento / pasivo |
|---|---|---|
| Strategy | tostado/naranja | Resource / Capability · Course of Action / (Value Stream) |
| Business | amarillo | Actor, Role, Collaboration, Interface / Process, Function, Interaction, Event, Service / Object, Contract, Representation, Product |
| Application | azul | Component, Collaboration, Interface / Function, Process, Interaction, Event, Service / Data Object |
| Technology | verde | Node, Device, System Software, Collaboration, Interface, Path, Communication Network / Function, Process, Interaction, Event, Service / Artifact |
| Physical (parte de Technology) | verde | Equipment, Facility, Distribution Network / — / Material |
| Motivation | violeta | Stakeholder, Driver, Assessment, Goal, Outcome, Principle, Requirement, Constraint, Meaning, Value |
| Implementation & Migration | rosa | — / Work Package, Implementation Event / Deliverable, Plateau, Gap |
| Composite (transversal) | — | Grouping, Location |

## Tipos de elemento y su ícono (esquina superior derecha)

El nodo es un rectángulo con el nombre y un **ícono de tipo** arriba a la derecha. Íconos clave:

**Active structure** (forma del recuadro + ícono):
- Actor → figura humana (stick figure).
- Role → ícono de "rol" (cilindro con línea) — recuadro normal.
- Collaboration → dos círculos superpuestos.
- Interface → "lollipop"/socket (círculo con tallo).
- Component (app) → rectángulo con dos pestañas (UML component).
- Node → caja 3D (paralelepípedo).
- Device → caja 3D con ícono de dispositivo.
- System Software → recuadro con ícono de software.
- Path / Communication Network → íconos de red.

**Behavior** (comportamiento):
- Process → **flecha** ancha (chevron) apuntando al flujo.
- Function → ícono de función (flecha redondeada / "cuchara").
- Interaction → círculo mitad-relleno.
- Event → forma de flecha entrante / bandera (extremo cóncavo).
- Service → **recuadro de extremos redondeados** (píldora).

**Passive structure:**
- Data Object / Business Object → rectángulo con **barra superior** (UML class-lite).
- Artifact → documento con **esquina doblada**.
- Representation → documento con **borde inferior ondulado**.
- Material → ícono físico.

**Motivation** (todos recuadro violeta con ícono propio): Goal (objetivo), Outcome, Requirement,
Constraint, Principle, Driver, Assessment, Stakeholder, Meaning (nube), Value (óvalo).

**Strategy:** Capability, Resource, Course of Action, Value Stream.
**Implementation & Migration:** Work Package, Deliverable (rectángulo esquina doblada),
Plateau, Gap, Implementation Event.

## Relaciones (línea + punta) y fuerza de derivación

**Estructurales** (fuerza débil→fuerte, para derivar la relación resumen):
`Realization < Assignment < Aggregation < Composition`

| Relación | Línea | Extremo | Significado |
|---|---|---|---|
| Composition | sólida | **rombo relleno** en el padre | todo-parte; el hijo no existe sin el padre |
| Aggregation | sólida | **rombo hueco** en el padre | agrupa; el hijo puede pertenecer a varios |
| Assignment | sólida | **bolita rellena** en el activo → **punta rellena** | el activo ejecuta el comportamiento (o rol/actor) |
| Realization | **punteada** | **triángulo hueco** en lo realizado | lo concreto realiza lo abstracto (Artifact→Data Object, Function→Service) |

**Dependencia** (fuerza débil→fuerte): `Association < Influence < Access < Serving`

| Relación | Línea | Extremo | Significado |
|---|---|---|---|
| Serving | sólida | **punta abierta** (flecha fina) | sirve a / es usado por (ex "Used By") |
| Access | **punteada** | punta abierta pequeña (opcional en 1 o ambos lados) | comportamiento lee/escribe un pasivo; ambas puntas = read/write |
| Influence | **guionada** | punta abierta, etiqueta **+/−** | un motivacional influye en otro (positivo/negativo) |
| Association | sólida | sin punta (opcionalmente dirigida) | relación "de último recurso"; catch-all |

**Dinámicas:**

| Relación | Línea | Extremo | Significado |
|---|---|---|---|
| Triggering | sólida | **punta rellena** | disparo causal: b ocurre después de a |
| Flow | **guionada** | **punta rellena** | transferencia (información/valor) de a hacia b |

**Otras:**
- **Specialization** — línea sólida + **triángulo hueco**: "es un tipo de" (is-a). (Igual que Realization pero línea sólida.)
- **Junction** — no es relación sino **conector**: círculo pequeño **relleno = AND**, **hueco = OR (XOR)**. Une relaciones del mismo tipo (Trigger/Flow/Access/Serving/Assignment/etc).

**Anidamiento (nesting):** Composition, Aggregation, Assignment y Realization (las estructurales)
pueden dibujarse metiendo un elemento **dentro** de otro en vez de con una línea (SPEC §8.2:
pools/lanes BPMN y contenedores). Riesgo: se pierde de vista qué relación es.

## Direccionalidad (para validación y derivación)

Todas las estructurales y de dependencia son **direccionales** salvo Association (existe dirigida y
no dirigida). Bajo el supuesto "worst case", Composition/Aggregation crean dependencia en **ambos**
sentidos. Esto importa para el `impact` (BFS) y para calcular relaciones derivadas.

## Mapeo con el registry v1 de ArqHub

El `registry` (§4.2) usa un **subconjunto canónico** intencionalmente reducido. Correspondencia:
- `kind` canónico → tipo ArchiMate concreto ya está en `KIND_MAPPINGS`.
- Relaciones canónicas → `RELATION_MAPPINGS` (serving, triggering, access, composition, aggregation,
  assignment, realization, association, specialization, +flow/uses como alias).
- Al extender: sumar tipos nuevos SOLO vía `registry.py` (fuente única de verdad), nunca hardcodeados
  en el canvas. El canvas lee capa/ícono/color derivados del registry por `/meta/registry`.
