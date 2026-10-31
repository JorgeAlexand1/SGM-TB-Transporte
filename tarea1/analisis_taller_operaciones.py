#!/usr/bin/env python3
"""Analisis reproducible del taller de calidad del modulo math_operations."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REQUIRED_COLUMNS = [
    "Prueba_ID",
    "Operacion",
    "Tipo_Error",
    "Entrada",
    "Resultado_Esperado",
    "Resultado_Observado_Inicial",
    "Impacto",
    "Severidad",
    "Correccion",
    "Estado_Final",
]

ISHIKAWA_CAUSES = {
    "Metodo": ["Formula incorrecta", "Clave division inconsistente"],
    "Sistema / codigo": ["Nombres pow/power", "Ramas no cubiertas"],
    "Persona": ["Revision manual insuficiente", "Requisitos interpretados de forma distinta"],
    "Herramientas": ["Cobertura de pruebas inicial baja", "Faltaba prueba de API"],
    "Datos": ["Divisor cero", "Raiz negativa", "Porcentaje fuera de escala"],
}

PDCA_ROWS = [
    ("Plan", "Definir errores en las 5 operaciones nuevas", "Hallazgos", "5 casos delimitados", "5 casos"),
    ("Do", "Corregir nombres, formulas y validaciones", "Correcciones", "5 correcciones", "5 aplicadas"),
    ("Check", "Ejecutar las pruebas automatizadas", "Fallos de pruebas", "0 fallos", "0 de 11"),
    ("Act", "Conservar pruebas y restricciones para futuros cambios", "Cobertura de operaciones", "5 de 5", "5 de 5"),
]

DMAIC_ROWS = [
    ("Define", "Resultados incorrectos o no controlados", "Alcance", "5 operaciones", "5 operaciones"),
    ("Measure", "Medir frecuencia, severidad e impacto", "Hallazgos", "5 hallazgos", "5; 3 criticos; 2 altos"),
    ("Analyze", "Relacionar hallazgos con causas raiz", "Causas identificadas", "100% clasificados", "5 de 5 en Ishikawa"),
    ("Improve", "Corregir formulas, claves y validaciones", "Correcciones", "5 correcciones", "5 aplicadas"),
    ("Control", "Repetir pruebas despues de cada cambio", "Pruebas fallidas", "0 fallos", "0 de 11"),
]

PARETO_ORDER = ["pow", "sqrt", "percent", "avg", "division"]
PARETO_LABELS = {
    "pow": "Potencia\n(pow)",
    "sqrt": "Raiz Cuad.\n(sqrt)",
    "percent": "Porcentaje\n(percent)",
    "avg": "Promedio\n(avg)",
    "division": "Division\n(division)",
}
PARETO_COLORS = {
    "pow": "#ef4444",
    "sqrt": "#dc2626",
    "percent": "#f59e0b",
    "avg": "#fbbf24",
    "division": "#3b82f6",
}


def cargar_registro(csv_path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(csv_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(missing))
    return dataframe[REQUIRED_COLUMNS].copy()


def calcular_pareto(dataframe: pd.DataFrame) -> pd.DataFrame:
    frequencies = dataframe["Operacion"].value_counts()
    ordered_operations = [operation for operation in PARETO_ORDER if operation in frequencies]
    pareto = frequencies.reindex(ordered_operations).rename("Frecuencia").to_frame()
    pareto["Porcentaje"] = pareto["Frecuencia"] / pareto["Frecuencia"].sum() * 100
    pareto["Porcentaje_Acumulado"] = pareto["Porcentaje"].cumsum()
    return pareto


def guardar_pareto(dataframe: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    pareto = calcular_pareto(dataframe)
    print("\nPareto de errores por operacion:")
    print(pareto.round(2).to_string())

    figure, bars_axis = plt.subplots(figsize=(11, 6.5))
    line_axis = bars_axis.twinx()
    labels = [PARETO_LABELS.get(operation, operation) for operation in pareto.index]
    colors = [PARETO_COLORS.get(operation, "#176b87") for operation in pareto.index]
    bars = bars_axis.bar(pareto.index, pareto["Frecuencia"], color=colors)
    for bar, (_, row) in zip(bars, pareto.iterrows()):
        bars_axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.03,
            f"{int(row['Frecuencia'])} def.",
            ha="center",
            va="bottom",
            weight="bold",
        )
    line_axis.plot(
        pareto.index,
        pareto["Porcentaje_Acumulado"],
        color="#d1495b",
        marker="o",
        linewidth=2,
    )
    for index, (_, row) in enumerate(pareto.iterrows()):
        line_axis.text(
            index,
            row["Porcentaje_Acumulado"] + 3,
            f"{row['Porcentaje_Acumulado']:.0f}%",
            ha="center",
            va="bottom",
            color="#1e3a8a",
            weight="bold",
        )
    line_axis.axhline(80, color="#d1495b", linestyle="--", label="Umbral 80%")
    bars_axis.set_title(
        "Diagrama de Pareto: priorizacion de defectos en modulo matematico\n"
        "Distribucion uniforme de fallos criticos y logicos"
    )
    bars_axis.set_xlabel("Operacion")
    bars_axis.set_ylabel("Frecuencia de defectos detectados")
    bars_axis.set_xticks(range(len(labels)))
    bars_axis.set_xticklabels(labels)
    bars_axis.set_ylim(0, max(2, int(pareto["Frecuencia"].max()) + 1))
    line_axis.set_ylabel("Porcentaje acumulado")
    line_axis.set_ylim(0, 110)
    bars_axis.grid(axis="y", alpha=0.2)
    line_axis.legend(loc="center right")
    figure.text(
        0.5,
        0.02,
        "Criticos: pow y sqrt | Logicos: percent y avg | Validacion: division",
        ha="center",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "#fff7ed", "edgecolor": "#d97706"},
    )
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return pareto


def guardar_ishikawa(output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(13, 7))
    axis.set_xlim(0, 13)
    axis.set_ylim(0, 10)
    axis.axis("off")
    axis.plot([1, 11], [5, 5], color="#444444", linewidth=3)
    axis.text(
        11.2,
        5,
        "Errores en los resultados\ndel modulo de operaciones",
        ha="left",
        va="center",
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#e76f51", "edgecolor": "#9d2d1f"},
        color="white",
        weight="bold",
    )

    positions = [(3, 7.3, 1), (5.5, 7.3, 1), (3, 2.7, -1), (5.5, 2.7, -1), (8, 2.7, -1)]
    for (category, causes), (x, y, direction) in zip(ISHIKAWA_CAUSES.items(), positions):
        axis.plot([x, x + 1.3], [y, 5], color="#555555", linewidth=2)
        axis.text(
            x - 0.15,
            y + 0.2 * direction,
            category,
            ha="right",
            va="center",
            weight="bold",
            color="#176b87",
        )
        for index, cause in enumerate(causes):
            offset = index * 0.45
            axis.text(
                x - 0.15,
                y + direction * (0.65 + offset),
                "- " + cause,
                ha="right",
                va="center",
                fontsize=8,
            )
    figure.suptitle("Diagrama de Ishikawa: analisis de causas", fontsize=15, weight="bold")
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def guardar_tablas(dataframe: pd.DataFrame, output_dir: Path) -> None:
    errores = dataframe[
        [
            "Prueba_ID",
            "Operacion",
            "Tipo_Error",
            "Entrada",
            "Resultado_Esperado",
            "Resultado_Observado_Inicial",
            "Impacto",
            "Severidad",
            "Correccion",
            "Estado_Final",
        ]
    ]
    pdca = pd.DataFrame(
        PDCA_ROWS,
        columns=["Etapa", "Actividad", "Indicador", "Criterio", "Resultado"],
    )
    dmaic = pd.DataFrame(
        DMAIC_ROWS,
        columns=["Etapa", "Actividad", "Indicador", "Criterio", "Resultado"],
    )
    errores.to_csv(output_dir / "tabla_errores_encontrados.csv", index=False)
    pdca.to_csv(output_dir / "tabla_pdca.csv", index=False)
    dmaic.to_csv(output_dir / "tabla_six_sigma_dmaic.csv", index=False)

    sections = [
        ("Errores encontrados", errores),
        ("PDCA", pdca),
        ("Six Sigma DMAIC", dmaic),
    ]
    markdown = ["# Tablas del taller", ""]
    for title, table in sections:
        markdown.extend([f"## {title}", ""])
        markdown.append("| " + " | ".join(table.columns) + " |")
        markdown.append("| " + " | ".join(["---"] * len(table.columns)) + " |")
        for row in table.itertuples(index=False):
            markdown.append("| " + " | ".join(str(value) for value in row) + " |")
        markdown.append("")
    (output_dir / "tablas_taller.md").write_text("\n".join(markdown), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("registro_pruebas_operaciones.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("resultados_calidad"))
    args = parser.parse_args()

    dataframe = cargar_registro(args.csv)
    if dataframe.empty:
        raise ValueError("El registro de pruebas no puede estar vacio")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(args.output_dir / "registro_pruebas_operaciones.csv", index=False)
    pareto = guardar_pareto(dataframe, args.output_dir / "pareto_operaciones.png")
    guardar_ishikawa(args.output_dir / "ishikawa_operaciones.png")
    guardar_tablas(dataframe, args.output_dir)
    print("\nHallazgos registrados:", len(dataframe))
    print("Causas que alcanzan el 80%:", int((pareto["Porcentaje_Acumulado"] <= 80).sum()))
    print(
        "Artefactos generados: pareto_operaciones.png, ishikawa_operaciones.png, "
        "tabla_errores_encontrados.csv, tabla_pdca.csv, tabla_six_sigma_dmaic.csv, "
        "tablas_taller.md"
    )


if __name__ == "__main__":
    main()
