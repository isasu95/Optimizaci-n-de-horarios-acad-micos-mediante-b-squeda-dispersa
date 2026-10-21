# -*- coding: utf-8 -*-
"""
V5 - Optimización de horarios académicos mediante Búsqueda Dispersa
Facultad de Matemáticas Acapulco - UAGro

Datos base: PDF proporcionado por el usuario.

CARACTERÍSTICAS
- Python estándar: no requiere numpy, pandas ni matplotlib.
- Representación por bloques de 2 módulos.
- Receso fijo: módulo 3.
- Bloque especial 2 -> 4: atraviesa el receso y cuenta como 2 módulos de clase.
- Coloquio fijo: miércoles, módulo 4 (configurable).
- Restricciones duras: grupo, profesor, aula y módulos fijos.
- Objetivo blando: minimizar huecos y repeticiones innecesarias de una materia
  en el mismo día.
- Scatter Search: población inicial, RefSet por calidad/diversidad,
  combinación, reparación constructiva y búsqueda local.
- 30 corridas independientes para estadísticas.
- Imprime el mejor horario y puede guardarlo en CSV.

NOTA:
El PDF proporciona aulas, pero no establece una relación aula-grupo/materia.
Por eso V5 permite utilizar cualquier aula disponible, salvo que el usuario
configure restricciones específicas en RESTRICCIONES_AULAS.
"""

from __future__ import annotations

import csv
import math
import random
import statistics
import time
from dataclasses import dataclass
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

DIAS = ["Lun", "Mar", "Mie", "Jue", "Vie"]

# Módulos del horario original del proyecto.
HORAS = {
    1: "08:00-08:50",
    2: "08:50-09:40",
    3: "09:40-10:10 RECESO",
    4: "10:10-11:00",
    5: "11:00-11:50",
    6: "11:50-12:40",
    7: "12:40-13:30",
    8: "13:30-14:20",
    9: "14:20-15:10",
    10: "15:10-16:00",
}

RECESO = 3
COLOQUIO_FIJO = True
DIA_COLOQUIO = "Mie"
MODULO_COLOQUIO = 4

# Aulas que aparecen en el PDF.
AULAS = [
    "A1", "A2", "A3", "A4",
    "B1", "B2",
    "C3", "C5", "C6",
    "CENCOM1", "CENCOM2", "CENCOM3",
    "LAB. DE MOD. COG.",
]

# Cada elemento representa DOS módulos académicos.
# (2, 4) significa: módulo 2 + módulo 4, atravesando el receso.
BLOQUES_BASE = [
    (1, 2),
    (2, 4),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (8, 9),
    (9, 10),
]

# ============================================================
# 2. DATOS REALES DEL PDF
# ============================================================

# (grupo, materia, profesor, módulos_semana)
DATOS = [
    # ---------------- GRUPO 201 ----------------
    ("201", "Cálculo I", "MC. RAÚL SALAS VEGA", 6),
    ("201", "Álgebra Superior", "DR. GERARDO REYNA HERNÁNDEZ", 6),
    ("201", "Geometría Analítica I", "M.C. GEMA RUBÍ MORENO ALEJANDRÍ", 6),
    ("201", "Inglés II", "LIC. MA. TERESA OSORIO FLORES", 4),
    ("201", "Principios de Computación I", "DR. VIRGILIO CRUZ GUZMÁN", 6),
    ("201", "Habilidades para la Comunicación de Ideas", "DRA. THELMA GALENA MOYAHO", 4),
    ("201", "Análisis del Mundo Contemporáneo", "LIC. MA. TERESA OSORIO FLORES", 4),

    # ---------------- GRUPO 202 ----------------
    ("202", "Cálculo I", "M.C. JOSÉ GPE. TORRES SUÁREZ", 6),
    ("202", "Álgebra Superior", "DR. JESÚS NOYOLA RODRÍGUEZ", 6),
    ("202", "Geometría Analítica I", "DR. JOSÉ LUIS SÁNCHEZ SANTIESTEBAN", 6),
    ("202", "Inglés II", "LIC. MA. TERESA OSORIO FLORES", 4),
    ("202", "Principios de Computación I", "M.C. CESAR LÓPEZ GODOY", 6),
    ("202", "Habilidades para la Comunicación de Ideas", "DRA. THELMA GALENA MOYAHO", 4),
    ("202", "Análisis del Mundo Contemporáneo", "DRA. THELMA GALENA MOYAHO", 4),

    # ---------------- GRUPO 401 ----------------
    ("401", "Cálculo III", "M.C. MARÍO RODRÍGUEZ VÁLDES", 6),
    ("401", "Álgebra Lineal II", "DR. OMAR ROSARIO CAYETANO", 6),
    ("401", "Didáctica de las Matemáticas II", "DR. MARCELA FERRARI ESCOLA", 6),
    ("401", "Teoría de Números", "DR. JORGE CASTILLO MEDINA", 6),
    ("401", "Probabilidad", "M.C. ABRAHAM RIVERA MORALES", 6),
    ("401", "Opt. Obl. I Teoría de Conjuntos", "DR. JUAN CARLOS PICENO RIVERA", 6),

    # ---------------- GRUPO 402 ----------------
    ("402", "Cálculo III", "M.C. JORGE MANUEL S. CAMACHO ORIHUELA", 6),
    ("402", "Álgebra Lineal II", "M.C. RAÚL SALAS VEGA", 6),
    ("402", "Didáctica de las Matemáticas II", "M.C. JORGE MANUEL S. CAMACHO ORIHUELA", 6),
    ("402", "Teoría de Números", "DR. JUAN CARLOS PICENO RIVERA", 6),
    ("402", "Probabilidad", "DR. MIGUEL A. HERRERA MIRANDA", 6),
    ("402", "Opt. Obl. I (Elab. y Resolución de Problemas)", "M.C. GEMA RUBÍ MORENO ALEJANDRI", 6),

    # ---------------- GRUPOS 403-404 ----------------
    ("403", "Opt. Obl. I Muestreo Estadístico", "DR. AGUSTÍN SANTIAGO MORENO", 6),
    ("404", "Opt. Obl. I Arquitectura de Comp. y Sist. Oper.", "M.C. CESAR LÓPEZ GODOY", 6),

    # ---------------- GRUPOS 601-602 ----------------
    ("601", "Ecuaciones Diferenciales Ordinarias", "M.C. MARIO RODRÍGUEZ VÁLDES", 6),
    ("601", "Análisis Matemático I", "M.C. JOSÉ GUADALUPE DE LA TORRE SUÁREZ", 6),
    ("601", "Opt. Obl. V Análisis Numérico", "DR. JORGE CASTILLO MEDINA", 6),
    ("601", "Opt. Obl. VI Álgebra Moderna II", "M.C. IGNACIO MIRANDA VARGAS", 6),
    ("601", "Opt. Obl. VII Geometría Diferencial", "DR. EFRÉN MORALES AMAYA", 6),

    ("602", "Ecuaciones Diferenciales Ordinarias", "M.C. RAÚL SALAS VEGA", 6),
    ("602", "Análisis Matemático I", "M.C. IGNACIO MIRANDA VARGAS", 6),
    ("602", "Opt. Obl. V Métodos de Inv. en Mat. Edu.", "DRA. YURIDIA ARELLANO GARCÍA", 6),
    ("602", "Opt. Obl. VI Matemática Escolar I", "DRA. MARÍA E. MAGALI MÉNDEZ GUEVARA", 6),
    ("602", "Opt. Obl. VII Enfoques Teóricos en la Mat. Edu. II", "M.C. NANCY MARQUINA MOLINA", 6),

    # ---------------- GRUPOS 603-604 ----------------
    ("603", "Opt. Obl. V Inferencia Estadística", "DR. OCTAVIANO JUÁREZ ROMERO", 6),
    ("603", "Opt. Obl. VI Estadística Multivariada", "M.C. ABRAHAM RIVERA MORALES", 6),
    ("603", "Opt. Obl. VII Diseño y Análisis de Experimentos", "M.C. ABRAHAM RIVERA MORALES", 6),

    ("604", "Opt. Obl. V Bases de Datos", "M.C. MARISOL JUÁREZ CISNEROS", 6),
    ("604", "Redes", "DRA. THELMA GALEANA MOHAYO", 6),
    ("604", "Opt. Obl. VII Análisis y Diseño de Algoritmos", "DR. VIRGILIO CRUZ GUZMÁN", 6),

    # ---------------- GRUPO 801 ----------------
    ("801", "Seminario de Titulación", "DR. JOSÉ MARÍA SIGARRETA ALMIRA", 6),
    ("801", "Opt. Obl. X Variable Compleja II", "M.C. JOSÉ GUADALUPE DE LA TORRE SUÁREZ", 6),
    ("801", "Opt. II Análisis Funcional", "M.C. IGNACIO MIRANDA VARGAS", 6),
    ("801", "Opt. III Complementos de la Geometría", "DR. EFRÉN MORALES AMAYA", 6),

    # ---------------- GRUPO 802 ----------------
    ("802", "Seminario de Titulación", "DRA. MAGDALENA RIVERA ABRAJAN", 6),
    ("802", "Opt. XVI Modelación en la Matemática Educativa", "DR. MANUEL TREJO MARTÍNEZ", 6),
    ("802", "Opt. Obl. XVII Práctica Docente I", "M.C. JORGE MANUEL S. CAMACHO ORIHUELA", 6),
    ("802", "Opt. XV Historia de las Matemáticas", "DR. HERMES NOLASCO HESIQUIO", 6),

    # ---------------- GRUPO 803 ----------------
    ("803", "Seminario de Titulación", "DR. JOSÉ MARÍA SIGARRETA ALMIRA", 6),
    ("803", "Opt. Obl. XVII Estadística Bayesiana", "DR. OCTAVIANO JUÁREZ ROMERO", 6),
    ("803", "Opt. XVI Análisis de Supervivencia", "DR. AGUSTÍN SANTIAGO MORENO", 6),
    ("803", "Opt. XV Tópicos de Consultoría Estadística", "DR. MIGUEL A. HERRERA MIRANDA", 6),

    # ---------------- GRUPO 804 ----------------
    ("804", "Seminario de Titulación", "DRA. THELMA GALEANA MOHAYO", 6),
    ("804", "Opt. Obl. XV Inteligencia Artificial", "DR. VIRGILIO CRUZ GÚZMAN", 6),
    ("804", "Opt. XVII Temas Selectos de Análisis de Datos", "M.C. MARISOL JUÁREZ CALDERÓN", 6),
    ("804", "Opt. XVI Innovación en Tecnología Educativa", "M.C. CESAR LÓPEZ GODOY", 6),
]


@dataclass(frozen=True)
class Asignatura:
    id: int
    grupo: str
    materia: str
    profesor: str
    modulos: int


@dataclass(frozen=True)
class Bloque:
    asignatura_id: int
    sesion: int
    dia: str
    modulos: Tuple[int, ...]
    aula: str


# ============================================================
# 3. RESTRICCIONES DE AULAS (OPCIONAL)
# ============================================================

# Si posteriormente se conoce que una materia/grupo SOLO puede utilizar
# determinadas aulas, se puede escribir aquí:
# "LAB": ["CENCOM1", "CENCOM2"]
# Si una asignatura no aparece, puede utilizar cualquier aula.
RESTRICCIONES_AULAS: Dict[Tuple[str, str], List[str]] = {}


# ============================================================
# 4. PREPARACIÓN DE DATOS
# ============================================================

def construir_asignaturas() -> List[Asignatura]:
    resultado = []
    for i, (grupo, materia, profesor, modulos) in enumerate(DATOS):
        if modulos % 2 != 0:
            raise ValueError(f"Carga impar en {grupo} - {materia}: {modulos}")
        resultado.append(Asignatura(i, grupo, materia, profesor, modulos))
    return resultado


ASIGNATURAS = construir_asignaturas()
ASIG_POR_ID = {a.id: a for a in ASIGNATURAS}


def sesiones_por_asignatura() -> Dict[int, int]:
    return {a.id: a.modulos // 2 for a in ASIGNATURAS}


SESIONES = sesiones_por_asignatura()


def modulos_bloque(dia: str, bloque: Tuple[int, int]) -> Tuple[int, ...]:
    a, b = bloque
    # El bloque (2,4) representa dos módulos de clase separados por el receso.
    return (a, b)


def bloque_valido(dia: str, bloque: Tuple[int, int]) -> bool:
    mods = modulos_bloque(dia, bloque)
    if RECESO in mods:
        return False
    if COLOQUIO_FIJO and dia == DIA_COLOQUIO and MODULO_COLOQUIO in mods:
        return False
    return True


def bloques_disponibles() -> List[Tuple[str, Tuple[int, ...]]]:
    salida = []
    for dia in DIAS:
        for b in BLOQUES_BASE:
            if bloque_valido(dia, b):
                salida.append((dia, modulos_bloque(dia, b)))
    return salida


POSICIONES = bloques_disponibles()


# ============================================================
# 5. REPRESENTACIÓN DE UNA SOLUCIÓN
# ============================================================

# Una solución es una lista indexada por "sesiones globales".
# Cada elemento: (dia, modulos, aula)
# El orden de sesiones se fija una sola vez para facilitar combinación.

SESIONES_GLOBAL = []
for a in ASIGNATURAS:
    for s in range(SESIONES[a.id]):
        SESIONES_GLOBAL.append((a.id, s))

NUM_SESIONES = len(SESIONES_GLOBAL)


def aulas_permitidas(asig: Asignatura) -> List[str]:
    return RESTRICCIONES_AULAS.get((asig.grupo, asig.materia), AULAS)


def recursos_de_slot(dia: str, modulos: Tuple[int, ...]) -> List[Tuple[str, int]]:
    return [(dia, m) for m in modulos]


# ============================================================
# 6. CONSTRUCCIÓN FACTIBLE
# ============================================================

def conflicto_hard(
    asig: Asignatura,
    dia: str,
    modulos: Tuple[int, ...],
    aula: str,
    ocup_group,
    ocup_prof,
    ocup_aula,
) -> bool:
    for m in modulos:
        if (dia, m, asig.grupo) in ocup_group:
            return True
        if (dia, m, asig.profesor) in ocup_prof:
            return True
        if (dia, m, aula) in ocup_aula:
            return True
    return False


def registrar(
    asig: Asignatura,
    dia: str,
    modulos: Tuple[int, ...],
    aula: str,
    ocup_group,
    ocup_prof,
    ocup_aula,
):
    for m in modulos:
        ocup_group.add((dia, m, asig.grupo))
        ocup_prof.add((dia, m, asig.profesor))
        ocup_aula.add((dia, m, aula))


def borrar(
    asig: Asignatura,
    dia: str,
    modulos: Tuple[int, ...],
    aula: str,
    ocup_group,
    ocup_prof,
    ocup_aula,
):
    for m in modulos:
        ocup_group.discard((dia, m, asig.grupo))
        ocup_prof.discard((dia, m, asig.profesor))
        ocup_aula.discard((dia, m, aula))


def prioridad_asignaturas() -> List[int]:
    # Primero materias/profesores más restrictivos.
    carga_prof = defaultdict(int)
    for a in ASIGNATURAS:
        carga_prof[a.profesor] += SESIONES[a.id]
    return sorted(
        range(NUM_SESIONES),
        key=lambda i: (
            -carga_prof[ASIG_POR_ID[SESIONES_GLOBAL[i][0]].profesor],
            -ASIG_POR_ID[SESIONES_GLOBAL[i][0]].modulos,
            random.random(),
        ),
    )


def construir_solucion_factible() -> List[Tuple[str, Tuple[int, ...], str]]:
    """Construcción factible mediante coloreado greedy de sesiones.

    Cada sesión es un vértice. Dos sesiones son incompatibles si pertenecen
    al mismo grupo o si tienen el mismo profesor. Las posiciones temporales
    funcionan como colores. Las aulas se asignan después porque hay 13 aulas.
    """
    # Grafo de conflictos por grupo/profesor.
    grupos = defaultdict(list)
    profes = defaultdict(list)
    for idx, (aid, _ses) in enumerate(SESIONES_GLOBAL):
        a = ASIG_POR_ID[aid]
        grupos[a.grupo].append(idx)
        profes[a.profesor].append(idx)

    vecinos = [set() for _ in range(NUM_SESIONES)]
    for lista in list(grupos.values()) + list(profes.values()):
        for i in lista:
            vecinos[i].update(j for j in lista if j != i)

    # DSATUR: primero las sesiones con mayor saturación/grado.
    color = {}
    colores_usados = [set() for _ in range(NUM_SESIONES)]
    carga_color = [0] * len(POSICIONES)
    carga_slot = defaultdict(int)

    def elegir_vertice():
        libres = [i for i in range(NUM_SESIONES) if i not in color]
        return max(
            libres,
            key=lambda i: (
                len(colores_usados[i]),
                len(vecinos[i]),
                ASIG_POR_ID[SESIONES_GLOBAL[i][0]].modulos,
                random.random(),
            ),
        )

    # Ordenar posiciones para favorecer distribución semanal.
    posiciones = POSICIONES[:]
    random.shuffle(posiciones)

    while len(color) < NUM_SESIONES:
        i = elegir_vertice()
        prohibidos = {color[j] for j in vecinos[i] if j in color}

        # Elegimos un color no utilizado por vecinos, procurando no cargar
        # demasiado el mismo grupo en un día.
        aid, _ = SESIONES_GLOBAL[i]
        grupo = ASIG_POR_ID[aid].grupo
        usados_grupo = defaultdict(int)
        for j, c in color.items():
            aid2, _ = SESIONES_GLOBAL[j]
            if ASIG_POR_ID[aid2].grupo == grupo:
                usados_grupo[posiciones[c][0]] += 1

        candidatos = [
            c for c in range(len(posiciones))
            if c not in prohibidos
            and all(carga_slot[(posiciones[c][0], m)] < len(AULAS) for m in posiciones[c][1])
        ]
        if not candidatos:
            raise RuntimeError("No se encontró color temporal factible para una sesión.")

        # Preferir días menos cargados y cierta aleatoriedad.
        candidatos.sort(key=lambda c: (
            usados_grupo[posiciones[c][0]],
            random.random(),
        ))
        color[i] = candidatos[0]
        carga_color[candidatos[0]] += 1
        dia_c, mods_c = posiciones[candidatos[0]]
        for m_c in mods_c:
            carga_slot[(dia_c, m_c)] += 1
        for v in vecinos[i]:
            if v not in color:
                colores_usados[v].add(candidatos[0])

    # Asignar aulas sin conflictos. Como hay muchas aulas, basta con una
    # coloración greedy adicional por cada posición temporal.
    sol = [None] * NUM_SESIONES
    ocup_aula = set()
    orden = list(range(NUM_SESIONES))
    random.shuffle(orden)

    for idx in orden:
        c = color[idx]
        dia, mods = posiciones[c]
        asig = ASIG_POR_ID[SESIONES_GLOBAL[idx][0]]
        aulas = aulas_permitidas(asig)[:]
        random.shuffle(aulas)
        aula = None
        for au in aulas:
            if all((dia, m, au) not in ocup_aula for m in mods):
                aula = au
                break
        if aula is None:
            # Si una restricción futura de aulas vuelve imposible el bloque,
            # reiniciamos la construcción completa.
            raise RuntimeError("No se encontró aula factible para una sesión.")
        sol[idx] = (dia, mods, aula)
        for m in mods:
            ocup_aula.add((dia, m, aula))

    return sol


# ============================================================
# 7. MÉTRICAS
# ============================================================

def validar(sol):
    cp = cg = ca = bi = 0
    ocup_group = defaultdict(list)
    ocup_prof = defaultdict(list)
    ocup_aula = defaultdict(list)

    for idx, asignacion in enumerate(sol):
        aid, _ = SESIONES_GLOBAL[idx]
        asig = ASIG_POR_ID[aid]
        dia, mods, aula = asignacion

        if len(mods) != 2 or RECESO in mods:
            bi += 1
        if COLOQUIO_FIJO and dia == DIA_COLOQUIO and MODULO_COLOQUIO in mods:
            bi += 1

        for m in mods:
            ocup_group[(dia, m, asig.grupo)].append(idx)
            ocup_prof[(dia, m, asig.profesor)].append(idx)
            ocup_aula[(dia, m, aula)].append(idx)

    cp = sum(max(0, len(v) - 1) for v in ocup_prof.values())
    cg = sum(max(0, len(v) - 1) for v in ocup_group.values())
    ca = sum(max(0, len(v) - 1) for v in ocup_aula.values())

    # Comprobar que cada asignatura tenga exactamente sus sesiones.
    esperadas = {a.id: SESIONES[a.id] for a in ASIGNATURAS}
    encontradas = defaultdict(int)
    for aid, _ in SESIONES_GLOBAL:
        encontradas[aid] += 1
    if esperadas != dict(encontradas):
        bi += 1

    return {
        "profesor": cp,
        "grupo": cg,
        "aula": ca,
        "bloque": bi,
    }


def huecos_por_grupo(sol) -> int:
    # Los huecos se calculan dentro del primer y último módulo de actividad,
    # ignorando el receso fijo.
    ocup = defaultdict(set)
    for idx, (dia, mods, _aula) in enumerate(sol):
        aid, _ = SESIONES_GLOBAL[idx]
        grupo = ASIG_POR_ID[aid].grupo
        for m in mods:
            ocup[(grupo, dia)].add(m)

    huecos = 0
    for (grupo, dia), mods in ocup.items():
        if not mods:
            continue
        lo, hi = min(mods), max(mods)
        for m in range(lo, hi + 1):
            if m == RECESO:
                continue
            if m not in mods:
                huecos += 1
    return huecos


def repeticiones_materia_dia(sol) -> int:
    # Penaliza más de una sesión de la misma materia en el mismo día.
    dias = defaultdict(set)
    rep = 0
    for idx, (dia, _mods, _aula) in enumerate(sol):
        aid, _ = SESIONES_GLOBAL[idx]
        clave = (aid, dia)
        if clave in dias:
            rep += 1
        else:
            dias[clave].add(dia)
    return rep


def objetivo(sol) -> float:
    v = validar(sol)
    # Los conflictos son duros. Los pesos altos garantizan que una solución
    # con conflicto sea mucho peor que una solución factible.
    return (
        100000 * v["profesor"]
        + 100000 * v["grupo"]
        + 100000 * v["aula"]
        + 100000 * v["bloque"]
        + 10 * huecos_por_grupo(sol)
        + 3 * repeticiones_materia_dia(sol)
    )


def firma(sol):
    return tuple((d, m, a) for d, m, a in sol)


def diversidad(a, b) -> int:
    return sum(x != y for x, y in zip(a, b))


# ============================================================
# 8. REPARACIÓN Y MOVIMIENTOS
# ============================================================

def es_factible(sol) -> bool:
    v = validar(sol)
    return all(x == 0 for x in v.values())


def reconstruir_con_bloques(fijos: Dict[int, Tuple[str, Tuple[int, ...], str]]):
    sol = [None] * NUM_SESIONES
    ocup_group, ocup_prof, ocup_aula = set(), set(), set()

    # Insertar primero los bloques heredados que no entren en conflicto.
    indices = list(fijos.keys())
    random.shuffle(indices)
    descartados = []

    for idx in indices:
        aid, _ = SESIONES_GLOBAL[idx]
        asig = ASIG_POR_ID[aid]
        dia, mods, aula = fijos[idx]
        if not bloque_valido(dia, (mods[0], mods[-1])):
            descartados.append(idx)
            continue
        if conflicto_hard(asig, dia, mods, aula,
                          ocup_group, ocup_prof, ocup_aula):
            descartados.append(idx)
            continue
        sol[idx] = (dia, mods, aula)
        registrar(asig, dia, mods, aula, ocup_group, ocup_prof, ocup_aula)

    # Completar todo lo que no pudo heredarse.
    faltantes = [i for i in range(NUM_SESIONES) if sol[i] is None]
    random.shuffle(faltantes)

    for idx in faltantes:
        aid, _ = SESIONES_GLOBAL[idx]
        asig = ASIG_POR_ID[aid]
        candidatos = []
        posiciones = POSICIONES[:]
        random.shuffle(posiciones)
        for dia, mods in posiciones:
            for aula in aulas_permitidas(asig):
                if not conflicto_hard(asig, dia, mods, aula,
                                      ocup_group, ocup_prof, ocup_aula):
                    # Favorecer diversidad: pequeña aleatoriedad.
                    costo = random.random() * 10
                    candidatos.append((costo, dia, mods, aula))
        if not candidatos:
            return construir_solucion_factible()
        _, dia, mods, aula = min(candidatos, key=lambda x: x[0])
        sol[idx] = (dia, mods, aula)
        registrar(asig, dia, mods, aula, ocup_group, ocup_prof, ocup_aula)

    return sol


def movimiento_factible(sol, idx, nueva):
    # Se reconstruye la ocupación excluyendo el bloque que se moverá.
    aid, _ = SESIONES_GLOBAL[idx]
    asig = ASIG_POR_ID[aid]
    dia_n, mods_n, aula_n = nueva

    if not bloque_valido(dia_n, (mods_n[0], mods_n[-1])):
        return False

    og, op, oa = set(), set(), set()
    for j, asignacion in enumerate(sol):
        if j == idx:
            continue
        aid2, _ = SESIONES_GLOBAL[j]
        a2 = ASIG_POR_ID[aid2]
        d, mods, au = asignacion
        registrar(a2, d, mods, au, og, op, oa)

    return not conflicto_hard(asig, dia_n, mods_n, aula_n, og, op, oa)


def busqueda_local(sol, max_movimientos=250):
    actual = sol[:]
    mejor_val = objetivo(actual)

    for _ in range(max_movimientos):
        idx = random.randrange(NUM_SESIONES)
        aid, _ = SESIONES_GLOBAL[idx]
        asig = ASIG_POR_ID[aid]

        dia, mods, aula = actual[idx]
        candidatos = []
        for _k in range(6):
            nd, nmods = random.choice(POSICIONES)
            naula = random.choice(aulas_permitidas(asig))
            candidatos.append((nd, nmods, naula))

        mejor_vecino = None
        mejor_vecino_val = mejor_val
        for nueva in candidatos:
            if nueva == actual[idx]:
                continue
            if not movimiento_factible(actual, idx, nueva):
                continue
            vecino = actual[:]
            vecino[idx] = nueva
            val = objetivo(vecino)
            if val < mejor_vecino_val:
                mejor_vecino_val = val
                mejor_vecino = vecino

        if mejor_vecino is not None:
            actual = mejor_vecino
            mejor_val = mejor_vecino_val
        else:
            # No se encontró mejora en esta iteración.
            continue

    return actual


# ============================================================
# 9. SCATTER SEARCH
# ============================================================

class ScatterSearch:
    def __init__(
        self,
        poblacion=24,
        refset=8,
        iteraciones=60,
        elite=4,
        intensidad_local=120,
    ):
        self.poblacion = poblacion
        self.refset = refset
        self.iteraciones = iteraciones
        self.elite = elite
        self.intensidad_local = intensidad_local
        self.historial = []

    def generar_poblacion(self):
        poblacion = []
        firmas = set()
        intentos = 0
        max_intentos = max(500, self.poblacion * 100)
        while len(poblacion) < self.poblacion and intentos < max_intentos:
            intentos += 1
            try:
                sol = construir_solucion_factible()
            except RuntimeError:
                # La construcción es aleatoria; reiniciar es preferible a
                # introducir conflictos artificiales en la población inicial.
                continue
            sig = firma(sol)
            if sig not in firmas:
                firmas.add(sig)
                poblacion.append(sol)
        if len(poblacion) < self.poblacion:
            raise RuntimeError(
                f"Solo se pudieron generar {len(poblacion)} de {self.poblacion} "
                "soluciones factibles. Revisa restricciones adicionales."
            )
        return poblacion

    def construir_refset(self, poblacion):
        ordenadas = sorted(poblacion, key=objetivo)
        seleccionadas = ordenadas[:self.elite]
        restantes = ordenadas[self.elite:]

        while len(seleccionadas) < self.refset and restantes:
            # Seleccionar la solución que aporte mayor diversidad mínima.
            candidata = max(
                restantes,
                key=lambda s: min(diversidad(s, r) for r in seleccionadas)
            )
            seleccionadas.append(candidata)
            restantes.remove(candidata)
        return seleccionadas

    def combinar(self, p1, p2):
        # La combinación puede producir una herencia temporal difícil de reparar.
        # Se intenta varias veces y, si no es reparable, se conserva el mejor padre.
        for _intento in range(12):
            fijos = {}
            for i in range(NUM_SESIONES):
                if p1[i] == p2[i]:
                    fijos[i] = p1[i]
                elif random.random() < 0.5:
                    fijos[i] = p1[i]
                else:
                    fijos[i] = p2[i]
            try:
                return reconstruir_con_bloques(fijos)
            except RuntimeError:
                continue
        return p1[:] if objetivo(p1) <= objetivo(p2) else p2[:]

    def ejecutar(self):
        poblacion = self.generar_poblacion()
        ref = self.construir_refset(poblacion)
        mejor = min(ref, key=objetivo)
        mejor = busqueda_local(mejor, self.intensidad_local)
        mejor_val = objetivo(mejor)
        self.historial = [mejor_val]

        for _it in range(self.iteraciones):
            candidatos = []
            vistos = set()

            for i in range(len(ref)):
                for j in range(i + 1, len(ref)):
                    hijo = self.combinar(ref[i], ref[j])
                    hijo = busqueda_local(hijo, self.intensidad_local)
                    sig = firma(hijo)
                    if sig not in vistos:
                        vistos.add(sig)
                        candidatos.append(hijo)

            if not candidatos:
                break

            pool = ref + candidatos
            nueva_ref = self.construir_refset(pool)
            candidato_mejor = min(nueva_ref, key=objetivo)
            val = objetivo(candidato_mejor)

            if val < mejor_val:
                mejor = candidato_mejor
                mejor_val = val

            ref = nueva_ref
            self.historial.append(mejor_val)

            if mejor_val == 0:
                # 0 es óptimo para esta función objetivo.
                break

        return mejor


# ============================================================
# 10. PRESENTACIÓN DE RESULTADOS
# ============================================================

def nombre_bloque(mods):
    return "/".join(str(x) for x in mods)


def imprimir_resumen(sol, titulo="MEJOR SOLUCIÓN"):
    v = validar(sol)
    h = huecos_por_grupo(sol)
    r = repeticiones_materia_dia(sol)
    z = objetivo(sol)

    print("\n" + "=" * 110)
    print(titulo)
    print("=" * 110)
    print(f"Función objetivo Z : {z:.0f}")
    print(f"Conflictos profesor: {v['profesor']}")
    print(f"Conflictos grupo   : {v['grupo']}")
    print(f"Conflictos aula    : {v['aula']}")
    print(f"Bloques inválidos  : {v['bloque']}")
    print(f"Huecos             : {h}")
    print(f"Repeticiones/día   : {r}")
    print(f"Factible            : {'SÍ' if es_factible(sol) else 'NO'}")

    print("\nHORARIO ORDENADO POR GRUPO")
    print("-" * 110)

    por_grupo = defaultdict(list)
    for idx, asignacion in enumerate(sol):
        aid, sesion = SESIONES_GLOBAL[idx]
        a = ASIG_POR_ID[aid]
        dia, mods, aula = asignacion
        por_grupo[a.grupo].append((dia, mods, aula, a.materia, a.profesor, sesion + 1))

    orden_dia = {d: i for i, d in enumerate(DIAS)}
    orden_mod = {m: i for i, m in enumerate(range(1, 11))}

    for grupo in sorted(por_grupo):
        print(f"\nGRUPO {grupo}")
        filas = sorted(
            por_grupo[grupo],
            key=lambda x: (orden_dia[x[0]], min(x[1]))
        )
        for dia, mods, aula, materia, profesor, ses in filas:
            horas = " / ".join(HORAS[m].replace(" RECESO", "") for m in mods)
            print(f"  {dia} | {horas:25} | {aula:15} | {materia:45} | {profesor}")


def guardar_csv(sol, ruta="horario_V5.csv"):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "Grupo", "Materia", "Profesor", "Sesión", "Día",
            "Módulos", "Horario", "Aula"
        ])
        filas = []
        for idx, (dia, mods, aula) in enumerate(sol):
            aid, ses = SESIONES_GLOBAL[idx]
            a = ASIG_POR_ID[aid]
            horario = " / ".join(HORAS[m].replace(" RECESO", "") for m in mods)
            filas.append((
                a.grupo, a.materia, a.profesor, ses + 1,
                dia, nombre_bloque(mods), horario, aula
            ))
        filas.sort(key=lambda x: (x[0], DIAS.index(x[4]), min(int(m) for m in x[5].split("/"))))
        w.writerows(filas)
    return ruta


def guardar_convergencia(historial, ruta="convergencia_V5.csv"):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Iteracion", "Mejor_Z"])
        for i, z in enumerate(historial):
            w.writerow([i, z])
    return ruta


# ============================================================
# 11. EXPERIMENTO MULTICORRIDA
# ============================================================

def experimento(corridas=30, semilla_base=20261008):
    resultados = []
    mejor_global = None
    mejor_z = float("inf")
    peor_z = float("-inf")
    historial_mejor = []

    print("\nINICIANDO EXPERIMENTO")
    print(f"Asignaturas: {len(ASIGNATURAS)}")
    print(f"Sesiones de 2 módulos: {NUM_SESIONES}")
    print(f"Aulas disponibles: {len(AULAS)}")
    print(f"Corridas: {corridas}")

    for corrida in range(1, corridas + 1):
        random.seed(semilla_base + corrida)
        inicio = time.perf_counter()
        ss = ScatterSearch(
            poblacion=8,
            refset=4,
            iteraciones=8,
            elite=2,
            intensidad_local=5,
        )
        sol = ss.ejecutar()
        tiempo = time.perf_counter() - inicio
        z = objetivo(sol)
        v = validar(sol)
        resultados.append((z, tiempo, v, sol))

        if z < mejor_z:
            mejor_z = z
            mejor_global = sol
            historial_mejor = ss.historial[:]

        peor_z = max(peor_z, z)
        print(
            f"Corrida {corrida:02d}: Z={z:8.0f} | "
            f"CP={v['profesor']} CG={v['grupo']} CA={v['aula']} BI={v['bloque']} | "
            f"{tiempo:6.2f}s"
        )

    zs = [r[0] for r in resultados]
    tiempos = [r[1] for r in resultados]

    print("\n" + "=" * 80)
    print("ESTADÍSTICAS")
    print("=" * 80)
    print(f"Mejor Z       : {min(zs):.0f}")
    print(f"Peor Z        : {max(zs):.0f}")
    print(f"Promedio Z    : {statistics.mean(zs):.2f}")
    print(f"Desv. estándar: {statistics.pstdev(zs):.2f}")
    print(f"Tiempo medio  : {statistics.mean(tiempos):.3f} s")
    print(f"Corridas Z=0  : {sum(z == 0 for z in zs)}/{len(zs)}")

    return mejor_global, historial_mejor, resultados


# ============================================================
# 12. PROGRAMA PRINCIPAL
# ============================================================

def main():
    print("=" * 80)
    print("V5 - BÚSQUEDA DISPERSA PARA HORARIOS ACADÉMICOS")
    print("Facultad de Matemáticas Acapulco - UAGro")
    print("=" * 80)

    # Una corrida principal para mostrar el horario.
    random.seed(20261008)
    inicio = time.perf_counter()
    ss = ScatterSearch(
        poblacion=8,
        refset=4,
        iteraciones=8,
        elite=2,
        intensidad_local=5,
    )
    mejor = ss.ejecutar()
    tiempo = time.perf_counter() - inicio

    imprimir_resumen(mejor, "MEJOR SOLUCIÓN DE LA CORRIDA PRINCIPAL")
    print(f"Tiempo de la corrida principal: {tiempo:.3f} s")

    guardar_csv(mejor, "horario_V5_mejor.csv")
    guardar_convergencia(ss.historial, "convergencia_V5.csv")
    print("\nArchivos generados:")
    print("  - horario_V5_mejor.csv")
    print("  - convergencia_V5.csv")

    # Experimento estadístico para el cartel/congreso.
    mejor_global, historial, resultados = experimento(corridas=30)
    guardar_csv(mejor_global, "horario_V5_mejor_30_corridas.csv")
    guardar_convergencia(historial, "convergencia_V5_mejor_global.csv")

    imprimir_resumen(mejor_global, "MEJOR SOLUCIÓN DE LAS 30 CORRIDAS")


if __name__ == "__main__":
    main()
