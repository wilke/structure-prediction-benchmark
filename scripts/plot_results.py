#!/usr/bin/env python3
"""
Generate comparison plots from aggregated experiment metrics.

Produces:
  1. Per-tool quality bar charts (Experiment 1)
  2. Cross-tool heatmaps (Experiment 2)
  3. MSA impact paired bar charts (Experiment 3)
  4. MSA depth learning curves (Experiment 4)
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns


# Consistent color palette for tools
TOOL_COLORS = {
    "alphafold": "#4285F4",   # Google blue
    "boltz": "#EA4335",       # Red
    "chai": "#34A853",        # Green
    "esmfold": "#FBBC05",     # Yellow/gold
}

TOOL_ORDER = ["alphafold", "boltz", "chai", "esmfold"]

MSA_CONDITION_COLORS = {
    "no_msa": "#E0E0E0",
    "with_msa": "#4285F4",
    "default": "#9E9E9E",
}


def load_metrics(csv_path: str) -> pd.DataFrame:
    """Load aggregated metrics CSV."""
    df = pd.read_csv(csv_path)
    # Normalize tool names
    df["tool"] = df["tool"].str.lower().str.strip()
    return df


def plot_experiment1_bars(df: pd.DataFrame, output_dir: Path):
    """Bar charts comparing per-tool quality metrics against experimental."""
    exp1 = df[df["msa_condition"].isin(["default", "with_msa", "no_msa"])]
    if exp1.empty:
        print("  No Experiment 1 data found, skipping.")
        return

    metrics = ["tm_score", "gdt_ts", "gdt_ha"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 6))
    if len(metrics) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics):
        data = exp1.groupby("tool")[metric].agg(["mean", "std"]).reindex(TOOL_ORDER).dropna()
        colors = [TOOL_COLORS.get(t, "#999") for t in data.index]
        bars = ax.bar(data.index, data["mean"], yerr=data["std"],
                      color=colors, capsize=4, edgecolor="black", linewidth=0.5)
        ax.set_ylabel(metric.replace("_", " ").upper())
        ax.set_ylim(0, 1.05)
        ax.set_title(f"{metric.replace('_', ' ').upper()} by Tool")
        ax.tick_params(axis="x", rotation=30)

    fig.suptitle("Experiment 1: Prediction Quality vs Experimental (Default Settings)", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "exp1_quality_bars.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved exp1_quality_bars.png")

    # RMSD (lower is better — separate plot)
    fig, ax = plt.subplots(figsize=(6, 5))
    rmsd_data = exp1.groupby("tool")["rmsd"].agg(["mean", "std"]).reindex(TOOL_ORDER).dropna()
    colors = [TOOL_COLORS.get(t, "#999") for t in rmsd_data.index]
    ax.bar(rmsd_data.index, rmsd_data["mean"], yerr=rmsd_data["std"],
           color=colors, capsize=4, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("RMSD (Å)")
    ax.set_title("Experiment 1: RMSD by Tool (lower is better)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(output_dir / "exp1_rmsd_bars.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved exp1_rmsd_bars.png")


def plot_experiment2_heatmap(df: pd.DataFrame, output_dir: Path):
    """Cross-tool TM-score heatmap for each target."""
    # This works with batch comparison CSV data
    # For now, create summary heatmap of mean TM-scores
    exp_data = df[df["msa_condition"].isin(["default", "with_msa"])]
    if exp_data.empty:
        print("  No Experiment 2 data found, skipping.")
        return

    pivot = exp_data.pivot_table(
        values="tm_score",
        index="target_id",
        columns="tool",
        aggfunc="mean",
    )

    if pivot.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(6, len(pivot) * 0.5 + 2)))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".3f",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        ax=ax,
        linewidths=0.5,
    )
    ax.set_title("TM-score: Tool × Target (vs Experimental)")
    ax.set_ylabel("Target")
    ax.set_xlabel("Tool")
    fig.tight_layout()
    fig.savefig(output_dir / "exp2_cross_tool_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved exp2_cross_tool_heatmap.png")


def plot_experiment3_msa_impact(df: pd.DataFrame, output_dir: Path):
    """Paired bar charts: with-MSA vs without-MSA for each tool."""
    exp3 = df[df["msa_condition"].isin(["with_msa", "no_msa"])]
    if exp3.empty:
        print("  No Experiment 3 data found, skipping.")
        return

    metrics = ["tm_score", "rmsd", "gdt_ts"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 6))

    tools = [t for t in TOOL_ORDER if t in exp3["tool"].unique()]
    x = np.arange(len(tools))
    width = 0.35

    for ax, metric in zip(axes, metrics):
        no_msa = exp3[exp3["msa_condition"] == "no_msa"].groupby("tool")[metric].mean()
        with_msa = exp3[exp3["msa_condition"] == "with_msa"].groupby("tool")[metric].mean()

        no_msa_vals = [no_msa.get(t, 0) for t in tools]
        with_msa_vals = [with_msa.get(t, 0) for t in tools]

        ax.bar(x - width / 2, no_msa_vals, width, label="No MSA",
               color="#E0E0E0", edgecolor="black", linewidth=0.5)
        ax.bar(x + width / 2, with_msa_vals, width, label="With MSA",
               color="#4285F4", edgecolor="black", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(tools, rotation=30)
        ax.set_ylabel(metric.replace("_", " ").upper())
        ax.set_title(metric.replace("_", " ").upper())
        ax.legend()

    fig.suptitle("Experiment 3: MSA Impact on Prediction Quality", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "exp3_msa_impact.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved exp3_msa_impact.png")

    # MSA source comparison (MMseqs2 vs JackHMMER)
    source_data = exp3[exp3["msa_source"].isin(["mmseqs2", "jackhmmer"])]
    if not source_data.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        for tool in tools:
            tool_data = source_data[source_data["tool"] == tool]
            for source in ["mmseqs2", "jackhmmer"]:
                subset = tool_data[tool_data["msa_source"] == source]
                if not subset.empty:
                    label = f"{tool} ({source})"
                    marker = "o" if source == "mmseqs2" else "s"
                    ax.scatter(
                        subset["tm_score"].mean(),
                        subset["rmsd"].mean(),
                        label=label,
                        s=100,
                        marker=marker,
                        color=TOOL_COLORS.get(tool, "#999"),
                        edgecolors="black",
                    )
        ax.set_xlabel("TM-score (higher is better)")
        ax.set_ylabel("RMSD (Å, lower is better)")
        ax.set_title("MSA Source Comparison: MMseqs2 vs JackHMMER")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(output_dir / "exp3_msa_source.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved exp3_msa_source.png")


def plot_experiment4_depth_curves(df: pd.DataFrame, output_dir: Path):
    """Learning curves: quality metric vs MSA depth."""
    exp4 = df[df["msa_depth"].notna()].copy()
    exp4 = exp4[exp4["msa_depth"] != ""]
    if exp4.empty:
        print("  No Experiment 4 data found, skipping.")
        return

    # Convert depth to numeric (treat "full" as a large number for sorting)
    exp4["depth_numeric"] = exp4["msa_depth"].apply(
        lambda x: 10000 if str(x).lower() == "full" else int(x)
    )

    metrics = ["tm_score", "rmsd", "gdt_ts"]

    for msa_source in ["mmseqs2", "jackhmmer"]:
        source_data = exp4[exp4["msa_source"] == msa_source]
        if source_data.empty:
            continue

        fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))

        for ax, metric in zip(axes, metrics):
            for tool in TOOL_ORDER:
                tool_data = source_data[source_data["tool"] == tool]
                if tool_data.empty:
                    continue

                grouped = tool_data.groupby("depth_numeric")[metric].agg(["mean", "std"])
                grouped = grouped.sort_index()

                ax.errorbar(
                    grouped.index,
                    grouped["mean"],
                    yerr=grouped["std"],
                    label=tool,
                    color=TOOL_COLORS.get(tool, "#999"),
                    marker="o",
                    capsize=3,
                    linewidth=1.5,
                )

            ax.set_xscale("log", base=2)
            ax.set_xlabel("MSA Depth (sequences)")
            ax.set_ylabel(metric.replace("_", " ").upper())
            ax.set_title(f"{metric.replace('_', ' ').upper()} vs MSA Depth")
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

            # Custom x-ticks
            depths = sorted(source_data["depth_numeric"].unique())
            ax.set_xticks(depths)
            ax.set_xticklabels(
                [str(d) if d < 10000 else "full" for d in depths],
                rotation=45,
                fontsize=8,
            )

        fig.suptitle(f"Experiment 4: MSA Depth Sensitivity ({msa_source})", y=1.02)
        fig.tight_layout()
        fname = f"exp4_depth_curves_{msa_source}.png"
        fig.savefig(output_dir / fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {fname}")


def main():
    parser = argparse.ArgumentParser(description="Generate experiment comparison plots")
    parser.add_argument(
        "--metrics",
        type=str,
        default="results/all_metrics.csv",
        help="Path to aggregated metrics CSV",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/plots",
        help="Output directory for plot images",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_metrics(args.metrics)
    print(f"Loaded {len(df)} metric rows from {args.metrics}")

    print("\nPlotting Experiment 1...")
    plot_experiment1_bars(df, output_dir)

    print("\nPlotting Experiment 2...")
    plot_experiment2_heatmap(df, output_dir)

    print("\nPlotting Experiment 3...")
    plot_experiment3_msa_impact(df, output_dir)

    print("\nPlotting Experiment 4...")
    plot_experiment4_depth_curves(df, output_dir)

    print(f"\nAll plots saved to {output_dir}")


if __name__ == "__main__":
    main()
