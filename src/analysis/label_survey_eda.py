"""Target-centred EDA for the MBN Life title-label survey.

The target is ``hasBracketLabel`` rather than an article-quality score.  The
outputs describe how editorial labels occur in this frozen sample; they do not
make causal or quality claims about articles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

from src.parsing.mbn_index_parser import extract_bracket_label


PREFIX = "label_survey"
NUMERIC_FEATURES = ("title_chars", "title_token_count", "hour", "day_index")
KOREAN_FONT = "NanumGothic"


def _safe_corr(left: pd.Series, right: pd.Series, method: str) -> float:
    """Return a rounded correlation only when both inputs have variation."""
    paired = pd.concat([left, right], axis=1).dropna()
    if len(paired) < 3 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
        return float("nan")
    return round(float(paired.iloc[:, 0].corr(paired.iloc[:, 1], method=method)), 4)


def _rate_table(frame: pd.DataFrame, group_col: str) -> pd.DataFrame:
    result = (
        frame.groupby(group_col, dropna=False)["has_bracket_label"]
        .agg(article_count="size", labeled_count="sum", label_rate="mean")
        .reset_index()
    )
    result["label_rate"] = result["label_rate"].round(4)
    return result


def _save_figure(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _set_plot_style() -> None:
    # Matplotlib's cache can miss a system-installed Korean font in fresh venvs.
    # Register the file explicitly so saved PNG labels remain readable.
    font_name = KOREAN_FONT
    for font_path in font_manager.findSystemFonts():
        if Path(font_path).name.lower() == "nanumgothic.ttf":
            font_manager.fontManager.addfont(font_path)
            font_name = font_manager.FontProperties(fname=font_path).get_name()
            break
    plt.rcParams.update(
        {
            "font.family": font_name,
            "axes.unicode_minus": False,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "#FCFCFC",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _model_signal(enriched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return optional nonlinear rankings; empty frames are valid fallbacks."""
    columns = [c for c in NUMERIC_FEATURES if enriched[c].nunique(dropna=True) >= 2]
    empty_mi = pd.DataFrame(columns=["feature", "mutual_information"])
    empty_rf = pd.DataFrame(columns=["feature", "random_forest_importance"])
    if len(columns) == 0 or len(enriched) < 20:
        return empty_mi, empty_rf

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_selection import mutual_info_classif
    except ImportError:
        return empty_mi, empty_rf

    x = enriched.loc[:, columns].fillna(enriched.loc[:, columns].median())
    y = enriched["has_bracket_label"].astype(int)
    mi = mutual_info_classif(x, y, discrete_features=False, random_state=20260107)
    forest = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        random_state=20260107,
        n_jobs=-1,
    )
    forest.fit(x, y)
    mi_frame = (
        pd.DataFrame({"feature": columns, "mutual_information": mi})
        .sort_values("mutual_information", ascending=False)
        .reset_index(drop=True)
    )
    rf_frame = (
        pd.DataFrame({"feature": columns, "random_forest_importance": forest.feature_importances_})
        .sort_values("random_forest_importance", ascending=False)
        .reset_index(drop=True)
    )
    return mi_frame.round(4), rf_frame.round(4)


def build_label_survey_eda(article_index: pd.DataFrame, output_dir: str | Path) -> dict[str, Any]:
    """Create reproducible tables and four visual blocks for label-use EDA.

    Parameters
    ----------
    article_index:
        Validated 02a article index. Required fields are ``rawTitle``,
        ``publishedAt`` and ``hasBracketLabel``.
    output_dir:
        Directory where audit CSV files and PNG figures will be written.
    """
    required = {"articleId", "rawTitle", "publishedAt", "hasBracketLabel"}
    missing = required.difference(article_index.columns)
    if missing:
        raise ValueError(f"article_index is missing required EDA columns: {sorted(missing)}")

    _set_plot_style()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    enriched = article_index.copy()
    enriched["publishedAt"] = pd.to_datetime(enriched["publishedAt"], errors="coerce")
    if enriched["publishedAt"].isna().any():
        raise ValueError("publishedAt contains unparseable values; EDA cannot establish time features")
    enriched["has_bracket_label"] = enriched["hasBracketLabel"].astype(bool)
    enriched["raw_label"] = enriched["rawTitle"].map(extract_bracket_label)
    enriched["label_group"] = enriched["raw_label"].fillna("라벨 없음")
    enriched["title_chars"] = enriched["rawTitle"].str.len().astype(int)
    enriched["title_token_count"] = enriched["rawTitle"].str.findall(r"[가-힣A-Za-z0-9]+") .str.len().astype(int)
    enriched["hour"] = enriched["publishedAt"].dt.hour.astype(int)
    enriched["weekday"] = enriched["publishedAt"].dt.day_name().map(
        {"Monday": "월", "Tuesday": "화", "Wednesday": "수", "Thursday": "목", "Friday": "금", "Saturday": "토", "Sunday": "일"}
    )
    enriched["month"] = enriched["publishedAt"].dt.to_period("M").astype(str)
    enriched["day_index"] = (enriched["publishedAt"].dt.normalize() - enriched["publishedAt"].min().normalize()).dt.days.astype(int)
    enriched["hour_bucket"] = pd.cut(
        enriched["hour"], bins=[-1, 5, 11, 17, 23], labels=["새벽(0–5)", "오전(6–11)", "오후(12–17)", "저녁(18–23)"]
    )
    enriched["title_length_bucket"] = pd.qcut(
        enriched["title_chars"], q=4, duplicates="drop", labels=["짧음", "중하", "중상", "김"]
    )
    label_counts = enriched.loc[enriched["has_bracket_label"], "raw_label"].value_counts()
    enriched["raw_label_count"] = enriched["raw_label"].map(label_counts).fillna(0).astype(int)

    target_rate = float(enriched["has_bracket_label"].mean())
    contract = pd.DataFrame(
        [
            ("target", "has_bracket_label"),
            ("target_type", "binary editorial-label presence"),
            ("analysis_rows", len(enriched)),
            ("positive_rows", int(enriched["has_bracket_label"].sum())),
            ("negative_rows", int((~enriched["has_bracket_label"]).sum())),
            ("positive_rate", round(target_rate, 4)),
            ("source_scope", "MBN Life frozen title survey, 12 pages"),
            ("interpretation", "exploratory label-use pattern, not article quality or causal evidence"),
        ],
        columns=["contract_field", "value"],
    )
    monthly = _rate_table(enriched, "month")
    weekday = _rate_table(enriched, "weekday").set_index("weekday").reindex(["월", "화", "수", "목", "금", "토", "일"]).reset_index()
    hour = _rate_table(enriched, "hour_bucket")
    title_length = _rate_table(enriched, "title_length_bucket")
    def profile_block(frame: pd.DataFrame, group_col: str, profile_group: str) -> pd.DataFrame:
        return frame.rename(columns={group_col: "group_value"}).assign(profile_group=profile_group)[
            ["profile_group", "group_value", "article_count", "labeled_count", "label_rate"]
        ]

    profile = pd.concat(
        [
            profile_block(monthly, "month", "month"),
            profile_block(weekday, "weekday", "weekday"),
            profile_block(hour, "hour_bucket", "hour_bucket"),
            profile_block(title_length, "title_length_bucket", "title_length_bucket"),
        ],
        ignore_index=True,
    )

    correlations = pd.DataFrame(
        [
            {
                "feature": feature,
                "pearson_vs_label_presence": _safe_corr(enriched[feature], enriched["has_bracket_label"].astype(int), "pearson"),
                "spearman_vs_label_presence": _safe_corr(enriched[feature], enriched["has_bracket_label"].astype(int), "spearman"),
                "non_null_rows": int(enriched[feature].notna().sum()),
            }
            for feature in NUMERIC_FEATURES
        ]
    )
    label_signal = (
        enriched.loc[enriched["has_bracket_label"]]
        .groupby("raw_label", dropna=True)
        .agg(article_count=("articleId", "size"), median_title_chars=("title_chars", "median"), median_hour=("hour", "median"))
        .reset_index()
        .sort_values(["article_count", "raw_label"], ascending=[False, True])
    )
    label_signal["share_of_labeled_articles"] = (label_signal["article_count"] / max(1, int(enriched["has_bracket_label"].sum()))).round(4)
    mi_signal, rf_signal = _model_signal(enriched)
    target_variant = pd.DataFrame(
        [{"target_variant": "not_applicable", "reason": "hasBracketLabel is binary; no low/mid/high range variants exist."}]
    )
    top_rows = (
        enriched.loc[enriched["has_bracket_label"], ["articleId", "publishedAt", "raw_label", "raw_label_count", "rawTitle", "url"]]
        .sort_values(["raw_label_count", "publishedAt"], ascending=[False, False])
        .head(30)
    )

    tables = {
        "contract": output / f"{PREFIX}_eda_contract.csv",
        "target_profile": output / f"{PREFIX}_eda_target_profile.csv",
        "numeric_correlations": output / f"{PREFIX}_eda_numeric_correlations.csv",
        "target_variant_signal": output / f"{PREFIX}_eda_target_variant_signal.csv",
        "raw_label_signal": output / f"{PREFIX}_eda_raw_label_signal.csv",
        "mutual_info": output / f"{PREFIX}_eda_mutual_info.csv",
        "random_forest_feature_signal": output / f"{PREFIX}_eda_random_forest_feature_signal.csv",
        "top_rows": output / f"{PREFIX}_eda_top_rows.csv",
        "enriched_rows": output / f"{PREFIX}_eda_enriched_rows.csv",
    }
    for frame, key in (
        (contract, "contract"), (profile, "target_profile"), (correlations, "numeric_correlations"),
        (target_variant, "target_variant_signal"), (label_signal, "raw_label_signal"),
        (mi_signal, "mutual_info"), (rf_signal, "random_forest_feature_signal"),
        (top_rows, "top_rows"), (enriched, "enriched_rows"),
    ):
        frame.to_csv(tables[key], index=False, encoding="utf-8-sig")

    figures: dict[str, Path] = {}
    colors = {False: "#AAB7C4", True: "#1976D2"}

    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    axes[0, 0].axis("off")
    axes[0, 0].text(
        0.02, 0.93,
        "타깃 설계\n"
        "• y: 제목 선행 대괄호 라벨 존재 여부\n"
        f"• 표본: MBN Life 동결 조사 {len(enriched):,}건\n"
        f"• 라벨 있음: {int(enriched['has_bracket_label'].sum()):,}건 ({target_rate:.1%})\n\n"
        "관찰\n"
        "• 월·시간·제목 길이별 사용 패턴을 비교\n\n"
        "제한\n"
        "• 수집 기간과 Life 섹션에 한정\n"
        "• 패턴은 라벨 사용의 기술통계이며 품질·인과 증거가 아님",
        va="top", fontsize=12,
    )
    status = enriched["has_bracket_label"].value_counts().reindex([False, True], fill_value=0)
    axes[0, 1].bar(["라벨 없음", "라벨 있음"], status.values, color=[colors[False], colors[True]])
    axes[0, 1].set_title("라벨 존재 여부 (타깃 분포)")
    axes[0, 1].set_ylabel("기사 수")
    for x, value in enumerate(status.values):
        axes[0, 1].text(x, value + 3, f"{value:,}\n{value / len(enriched):.1%}", ha="center")
    top_labels = label_signal.head(10).sort_values("article_count")
    axes[1, 0].barh(top_labels["raw_label"], top_labels["article_count"], color="#2A9D8F")
    axes[1, 0].set_title("상위 원시 라벨 빈도")
    axes[1, 0].set_xlabel("라벨 기사 수")
    axes[1, 1].plot(monthly["month"], monthly["label_rate"] * 100, marker="o", color="#E76F51", linewidth=2)
    axes[1, 1].set_title("월별 라벨 사용률")
    axes[1, 1].set_ylabel("라벨 사용률 (%)")
    axes[1, 1].tick_params(axis="x", rotation=35)
    axes[1, 1].set_ylim(0, min(100, max(60, monthly["label_rate"].max() * 125)))
    figures["target_profile"] = output / f"{PREFIX}_eda_01_target_profile.png"
    _save_figure(fig, figures["target_profile"])

    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    corr_plot = correlations.melt(id_vars="feature", value_vars=["pearson_vs_label_presence", "spearman_vs_label_presence"], var_name="metric", value_name="correlation")
    pivot = corr_plot.pivot(index="feature", columns="metric", values="correlation").fillna(0)
    pivot.plot.barh(ax=axes[0, 0], color=["#6C8EBF", "#F4A261"])
    axes[0, 0].axvline(0, color="#555", linewidth=0.8)
    axes[0, 0].set_title("이진 타깃과 수치 특징의 상관")
    axes[0, 0].set_xlabel("상관계수")
    axes[0, 0].legend(["Pearson", "Spearman"], loc="lower right")
    ranking = mi_signal.merge(rf_signal, on="feature", how="outer").fillna(0).set_index("feature")
    if ranking.empty:
        axes[0, 1].text(0.5, 0.5, "scikit-learn 미설치로\n비선형 순위를 생략", ha="center", va="center")
        axes[0, 1].axis("off")
    else:
        ranking.plot.barh(ax=axes[0, 1], color=["#8AB17D", "#E9C46A"])
        axes[0, 1].set_title("비선형 특징 순위 (가설 탐색)")
        axes[0, 1].set_xlabel("상대 점수")
        axes[0, 1].legend(["Mutual information", "Random forest"], loc="lower right")
    title_length.plot(x="title_length_bucket", y="label_rate", kind="bar", legend=False, ax=axes[1, 0], color="#457B9D")
    axes[1, 0].set_title("제목 길이 구간별 라벨 사용률")
    axes[1, 0].set_xlabel("")
    axes[1, 0].set_ylabel("사용률")
    axes[1, 0].set_ylim(0, 1)
    hour.plot(x="hour_bucket", y="label_rate", kind="bar", legend=False, ax=axes[1, 1], color="#A8DADC")
    axes[1, 1].set_title("발행 시간대별 라벨 사용률")
    axes[1, 1].set_xlabel("")
    axes[1, 1].set_ylabel("사용률")
    axes[1, 1].set_ylim(0, 1)
    axes[1, 1].tick_params(axis="x", rotation=20)
    figures["feature_signal"] = output / f"{PREFIX}_eda_02_feature_signal_rank.png"
    _save_figure(fig, figures["feature_signal"])

    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    for present in (False, True):
        subset = enriched.loc[enriched["has_bracket_label"] == present]
        axes[0, 0].scatter(subset["publishedAt"], subset["hour"], s=28, alpha=0.7, label="라벨 있음" if present else "라벨 없음", color=colors[present])
    axes[0, 0].set_title("발행 시점 × 시간: 라벨 존재")
    axes[0, 0].set_ylabel("발행 시각")
    axes[0, 0].legend(loc="upper left")
    jitter = np.where(enriched["has_bracket_label"], 0.03, -0.03)
    axes[0, 1].scatter(enriched["title_chars"], enriched["has_bracket_label"].astype(int) + jitter, c=enriched["has_bracket_label"].map(colors), s=30, alpha=0.7)
    axes[0, 1].set_title("제목 길이 × 라벨 존재")
    axes[0, 1].set_xlabel("제목 글자 수")
    axes[0, 1].set_yticks([0, 1], ["라벨 없음", "라벨 있음"])
    axes[1, 0].scatter(enriched["day_index"], enriched["title_token_count"], c=enriched["has_bracket_label"].map(colors), s=24 + enriched["raw_label_count"] * 5, alpha=0.65)
    axes[1, 0].set_title("조사 기간 경과 × 제목 토큰 수")
    axes[1, 0].set_xlabel("첫 기사 이후 일수")
    axes[1, 0].set_ylabel("제목 토큰 수")
    bubble = label_signal.loc[label_signal["article_count"] >= 2].copy()
    axes[1, 1].scatter(bubble["article_count"], bubble["median_title_chars"], s=80 + bubble["article_count"] ** 2 * 3, color="#E76F51", alpha=0.7)
    for row in bubble.itertuples():
        axes[1, 1].annotate(row.raw_label, (row.article_count, row.median_title_chars), xytext=(4, 4), textcoords="offset points", fontsize=9)
    axes[1, 1].set_title("반복 라벨의 빈도 × 제목 길이")
    axes[1, 1].set_xlabel("라벨 기사 수 (버블 면적도 동일)")
    axes[1, 1].set_ylabel("라벨별 제목 글자 수 중앙값")
    figures["scatter_bubbles"] = output / f"{PREFIX}_eda_03_scatter_bubbles.png"
    _save_figure(fig, figures["scatter_bubbles"])

    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    weekday.plot(x="weekday", y="label_rate", kind="bar", legend=False, ax=axes[0, 0], color="#264653")
    axes[0, 0].set_title("요일별 라벨 사용률")
    axes[0, 0].set_xlabel("")
    axes[0, 0].set_ylabel("사용률")
    axes[0, 0].set_ylim(0, 1)
    month_count = monthly.set_index("month")["article_count"]
    month_count.plot.bar(ax=axes[0, 1], color="#B8DE6F")
    axes[0, 1].set_title("월별 표본 수")
    axes[0, 1].set_xlabel("")
    axes[0, 1].set_ylabel("기사 수")
    axes[0, 1].tick_params(axis="x", rotation=35)
    groups = [enriched.loc[~enriched["has_bracket_label"], "title_chars"], enriched.loc[enriched["has_bracket_label"], "title_chars"]]
    axes[1, 0].boxplot(groups, tick_labels=["라벨 없음", "라벨 있음"], patch_artist=True, boxprops={"facecolor": "#A8DADC"})
    axes[1, 0].set_title("라벨 존재별 제목 길이 분포")
    axes[1, 0].set_ylabel("제목 글자 수")
    axes[1, 1].axis("off")
    top_text = label_signal.head(6).assign(summary=lambda d: d["raw_label"] + "  " + d["article_count"].astype(str) + "건")
    axes[1, 1].text(0.03, 0.95, "반복 라벨 상위 6\n\n" + "\n".join(top_text["summary"]), va="top", fontsize=12)
    axes[1, 1].text(0.03, 0.23, "해석 원칙\n• 수치·모델 순위는 탐색 가설\n• 표본/기간 밖 일반화 금지\n• 라벨 없음은 결측이 아닌 관측 범주", va="top", fontsize=11, color="#495057")
    figures["group_diagnostics"] = output / f"{PREFIX}_eda_04_group_diagnostics.png"
    _save_figure(fig, figures["group_diagnostics"])

    return {
        "output_dir": str(output),
        "target": "hasBracketLabel",
        "rows": int(len(enriched)),
        "labeled_rows": int(enriched["has_bracket_label"].sum()),
        "label_rate": round(target_rate, 4),
        "tables": {key: str(path) for key, path in tables.items()},
        "figures": {key: str(path) for key, path in figures.items()},
    }
