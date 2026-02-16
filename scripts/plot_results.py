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
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats as scipy_stats


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


def plot_plddt_analysis(df: pd.DataFrame, output_dir: Path):
    """pLDDT as a direct metric: confidence comparison and calibration."""
    if "mean_plddt_predicted" not in df.columns:
        print("  No pLDDT data found, skipping.")
        return

    plddt_data = df.dropna(subset=["mean_plddt_predicted"])
    if plddt_data.empty:
        return

    # 1. Mean pLDDT by tool (intrinsic confidence)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    tool_plddt = plddt_data.groupby("tool")["mean_plddt_predicted"].agg(["mean", "std"])
    tool_plddt = tool_plddt.reindex(TOOL_ORDER).dropna()
    colors = [TOOL_COLORS.get(t, "#999") for t in tool_plddt.index]
    ax.bar(tool_plddt.index, tool_plddt["mean"], yerr=tool_plddt["std"],
           color=colors, capsize=4, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("Mean pLDDT (0–100)")
    ax.set_ylim(0, 105)
    ax.set_title("Intrinsic Confidence by Tool")
    ax.axhline(y=70, color="#10B981", linestyle="--", alpha=0.5, label="High conf (≥70)")
    ax.axhline(y=50, color="#EF4444", linestyle="--", alpha=0.5, label="Low conf (<50)")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=30)

    # 2. pLDDT vs TM-score scatter (calibration)
    ax = axes[1]
    for tool in TOOL_ORDER:
        subset = plddt_data[plddt_data["tool"] == tool]
        if subset.empty or "tm_score" not in subset.columns:
            continue
        ax.scatter(
            subset["mean_plddt_predicted"],
            subset["tm_score"],
            label=tool,
            color=TOOL_COLORS.get(tool, "#999"),
            s=40,
            alpha=0.7,
            edgecolors="black",
            linewidth=0.3,
        )
    ax.set_xlabel("Mean pLDDT (0–100)")
    ax.set_ylabel("TM-score vs Experimental")
    ax.set_title("Confidence vs Actual Accuracy")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("pLDDT Direct Analysis", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "plddt_analysis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved plddt_analysis.png")

    # 3. pLDDT with/without MSA comparison
    msa_data = plddt_data[plddt_data["msa_condition"].isin(["with_msa", "no_msa"])]
    if not msa_data.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        tools = [t for t in TOOL_ORDER if t in msa_data["tool"].unique()]
        x = np.arange(len(tools))
        width = 0.35

        no_msa = msa_data[msa_data["msa_condition"] == "no_msa"].groupby("tool")["mean_plddt_predicted"].mean()
        with_msa = msa_data[msa_data["msa_condition"] == "with_msa"].groupby("tool")["mean_plddt_predicted"].mean()

        ax.bar(x - width/2, [no_msa.get(t, 0) for t in tools], width,
               label="No MSA", color="#E0E0E0", edgecolor="black", linewidth=0.5)
        ax.bar(x + width/2, [with_msa.get(t, 0) for t in tools], width,
               label="With MSA", color="#4285F4", edgecolor="black", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(tools, rotation=30)
        ax.set_ylabel("Mean pLDDT (0–100)")
        ax.set_title("Model Confidence: MSA vs No-MSA")
        ax.set_ylim(0, 105)
        ax.axhline(y=70, color="#10B981", linestyle="--", alpha=0.5)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "plddt_msa_impact.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved plddt_msa_impact.png")

    # 4. High-confidence fraction by tool
    if "plddt_high_conf_fraction" in plddt_data.columns:
        hc_data = plddt_data.dropna(subset=["plddt_high_conf_fraction"])
        if not hc_data.empty:
            fig, ax = plt.subplots(figsize=(7, 5))
            tool_hc = hc_data.groupby("tool")["plddt_high_conf_fraction"].agg(["mean", "std"])
            tool_hc = tool_hc.reindex(TOOL_ORDER).dropna()
            colors = [TOOL_COLORS.get(t, "#999") for t in tool_hc.index]
            ax.bar(tool_hc.index, tool_hc["mean"] * 100, yerr=tool_hc["std"] * 100,
                   color=colors, capsize=4, edgecolor="black", linewidth=0.5)
            ax.set_ylabel("% Residues with pLDDT ≥ 70")
            ax.set_title("High-Confidence Fraction by Tool")
            ax.set_ylim(0, 105)
            ax.tick_params(axis="x", rotation=30)
            fig.tight_layout()
            fig.savefig(output_dir / "plddt_high_conf_fraction.png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"  Saved plddt_high_conf_fraction.png")


def compute_statistical_tests(df: pd.DataFrame, output_dir: Path):
    """Paired statistical tests: Wilcoxon signed-rank, bootstrap CI, effect size."""
    results = []

    # --- MSA impact: paired comparison per tool (with_msa vs no_msa) ---
    msa_data = df[df["msa_condition"].isin(["with_msa", "no_msa"])]
    for tool in TOOL_ORDER:
        tool_data = msa_data[msa_data["tool"] == tool]
        if tool_data.empty:
            continue
        for metric in ["tm_score", "rmsd", "gdt_ts"]:
            with_vals = tool_data[tool_data["msa_condition"] == "with_msa"].set_index("target_id")[metric]
            no_vals = tool_data[tool_data["msa_condition"] == "no_msa"].set_index("target_id")[metric]
            common = with_vals.index.intersection(no_vals.index)
            if len(common) < 3:
                continue
            w = with_vals.loc[common].values
            n = no_vals.loc[common].values
            diff = w - n

            # Wilcoxon signed-rank
            try:
                stat, pval = scipy_stats.wilcoxon(diff)
            except ValueError:
                stat, pval = np.nan, np.nan

            # Cohen's d
            d_mean = np.mean(diff)
            d_std = np.std(diff, ddof=1)
            cohens_d = d_mean / d_std if d_std > 0 else np.nan

            # Bootstrap 95% CI for mean difference
            rng = np.random.default_rng(42)
            boot_means = []
            for _ in range(10000):
                sample = rng.choice(diff, size=len(diff), replace=True)
                boot_means.append(np.mean(sample))
            ci_low, ci_high = np.percentile(boot_means, [2.5, 97.5])

            results.append({
                "comparison": f"{tool}: with_msa vs no_msa",
                "metric": metric,
                "n_targets": len(common),
                "mean_diff": round(d_mean, 4),
                "wilcoxon_stat": round(stat, 4) if not np.isnan(stat) else "",
                "p_value": round(pval, 6) if not np.isnan(pval) else "",
                "cohens_d": round(cohens_d, 3) if not np.isnan(cohens_d) else "",
                "ci_95_low": round(ci_low, 4),
                "ci_95_high": round(ci_high, 4),
            })

    # --- Cross-tool pairwise comparisons (Bonferroni-corrected) ---
    default_data = df[df["msa_condition"].isin(["default", "with_msa"])]
    n_tool_pairs = 0
    tool_pair_results = []
    for i, tool_a in enumerate(TOOL_ORDER):
        for tool_b in TOOL_ORDER[i + 1:]:
            n_tool_pairs += 1
            for metric in ["tm_score"]:
                a_vals = default_data[default_data["tool"] == tool_a].set_index("target_id")[metric]
                b_vals = default_data[default_data["tool"] == tool_b].set_index("target_id")[metric]
                common = a_vals.index.intersection(b_vals.index)
                if len(common) < 3:
                    continue
                a = a_vals.loc[common].values
                b = b_vals.loc[common].values
                diff = a - b

                try:
                    stat, pval = scipy_stats.wilcoxon(diff)
                except ValueError:
                    stat, pval = np.nan, np.nan

                d_mean = np.mean(diff)
                d_std = np.std(diff, ddof=1)
                cohens_d = d_mean / d_std if d_std > 0 else np.nan

                tool_pair_results.append({
                    "comparison": f"{tool_a} vs {tool_b}",
                    "metric": metric,
                    "n_targets": len(common),
                    "mean_diff": round(d_mean, 4),
                    "wilcoxon_stat": round(stat, 4) if not np.isnan(stat) else "",
                    "p_value_raw": pval,
                    "cohens_d": round(cohens_d, 3) if not np.isnan(cohens_d) else "",
                })

    # Apply Bonferroni correction
    for r in tool_pair_results:
        raw_p = r.pop("p_value_raw")
        if not np.isnan(raw_p):
            corrected = min(raw_p * n_tool_pairs, 1.0)
            r["p_value_bonferroni"] = round(corrected, 6)
        else:
            r["p_value_bonferroni"] = ""
        r["ci_95_low"] = ""
        r["ci_95_high"] = ""
        results.append(r)

    # Write results
    if results:
        outpath = output_dir / "statistical_tests.csv"
        fieldnames = [
            "comparison", "metric", "n_targets", "mean_diff",
            "wilcoxon_stat", "p_value", "p_value_bonferroni",
            "cohens_d", "ci_95_low", "ci_95_high",
        ]
        with open(outpath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"  Saved statistical_tests.csv ({len(results)} tests)")
    else:
        print("  No data available for statistical testing.")


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

    print("\nPlotting pLDDT analysis...")
    plot_plddt_analysis(df, output_dir)

    print("\nRunning statistical tests...")
    compute_statistical_tests(df, output_dir)

    print(f"\nAll plots saved to {output_dir}")


if __name__ == "__main__":
    main()
