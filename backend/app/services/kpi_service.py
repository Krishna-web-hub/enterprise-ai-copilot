"""
KPI Engine — Automated Business KPI Computation

Takes a structured dataset and auto-detects which KPIs make sense based on
column names and types, then computes them.

Auto-detection strategy:
- Numeric columns → totals, averages, min/max, standard deviation
- Date/time columns → time-based trends (monthly/weekly aggregation)
- Categorical columns (low cardinality) → value counts, top-N breakdown
- Columns with names matching business patterns (revenue, sales, profit,
  amount, quantity, price, cost) → highlighted as key metrics

Why auto-detect rather than requiring the user to configure KPIs?
- The platform's promise is "upload data, get insights" — forcing manual
  KPI configuration defeats that for new users
- For a portfolio demo, showing intelligent auto-detection is more
  impressive than a configuration form
- Power users can still pick specific columns via the API parameters

Output structure:
{
    "dataset_name": str,
    "row_count": int,
    "summary_kpis": [{name, value, type}],  # Headline numbers
    "numeric_stats": [{column, total, mean, min, max, std}],
    "category_breakdowns": [{column, top_values: [{value, count, percent}]}],
    "time_trends": [{period, metrics: {col: value}}],  # If date column found
}
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.models.dataset import Dataset
from app.core.storage import get_storage
from app.utils.file_readers import read_structured_file

# Column name patterns that suggest business-relevant metrics
REVENUE_PATTERNS = ("revenue", "sales", "income", "turnover")
PROFIT_PATTERNS = ("profit", "margin", "earnings", "net_income")
AMOUNT_PATTERNS = ("amount", "total", "sum", "value", "price", "cost", "charge")
QUANTITY_PATTERNS = ("quantity", "qty", "count", "units", "volume")
DATE_PATTERNS = ("date", "time", "timestamp", "created", "period", "month", "year")

STRUCTURED_TYPES = {"csv", "excel", "json"}
MAX_CATEGORY_VALUES = 10  # Max distinct values to consider a column "categorical"


class KPIServiceError(Exception):
    pass


class KPIService:
    """Computes auto-detected KPIs from structured datasets."""

    def compute_kpis(self, dataset: Dataset) -> dict:
        """
        Compute KPIs for a dataset.

        Returns a structured dict with summary KPIs, numeric stats,
        category breakdowns, and optional time trends.
        """
        if dataset.file_type not in STRUCTURED_TYPES:
            raise KPIServiceError(
                f"KPI computation requires structured data (CSV/Excel/JSON), "
                f"not '{dataset.file_type}' files."
            )

        file_path = self._resolve_path(dataset.file_path)
        if not file_path:
            raise KPIServiceError(f"Dataset file not found: {dataset.file_path}")

        df = read_structured_file(file_path, dataset.file_type)

        if df.empty:
            return {
                "dataset_name": dataset.name,
                "row_count": 0,
                "summary_kpis": [],
                "numeric_stats": [],
                "category_breakdowns": [],
                "time_trends": [],
            }

        numeric_cols = self._get_numeric_columns(df)
        categorical_cols = self._get_categorical_columns(df)
        date_col = self._detect_date_column(df)

        # Compute each section
        summary_kpis = self._compute_summary_kpis(df, numeric_cols)
        numeric_stats = self._compute_numeric_stats(df, numeric_cols)
        category_breakdowns = self._compute_category_breakdowns(df, categorical_cols)
        time_trends = self._compute_time_trends(df, numeric_cols, date_col) if date_col else []

        return {
            "dataset_name": dataset.name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "summary_kpis": summary_kpis,
            "numeric_stats": numeric_stats,
            "category_breakdowns": category_breakdowns,
            "time_trends": time_trends,
        }

    def generate_export_data(self, dataset: Dataset) -> dict[str, pd.DataFrame]:
        """
        Generate Power BI-ready export data: multiple DataFrames suitable for
        an Excel workbook with multiple sheets.

        Returns:
            {
                "raw_data": original DataFrame,
                "summary": single-row DataFrame with headline KPIs,
                "numeric_stats": stats per numeric column,
                "category_breakdown": value counts for categorical columns,
            }
        """
        if dataset.file_type not in STRUCTURED_TYPES:
            raise KPIServiceError(f"Export requires structured data, not '{dataset.file_type}'.")

        file_path = self._resolve_path(dataset.file_path)
        if not file_path:
            raise KPIServiceError(f"Dataset file not found: {dataset.file_path}")

        df = read_structured_file(file_path, dataset.file_type)
        numeric_cols = self._get_numeric_columns(df)
        categorical_cols = self._get_categorical_columns(df)

        # Summary sheet
        summary_data = {"Metric": [], "Value": []}
        summary_data["Metric"].append("Total Rows")
        summary_data["Value"].append(len(df))
        for col in numeric_cols:
            summary_data["Metric"].append(f"{col} - Total")
            summary_data["Value"].append(round(float(df[col].sum()), 2))
            summary_data["Metric"].append(f"{col} - Average")
            summary_data["Value"].append(round(float(df[col].mean()), 2))

        summary_df = pd.DataFrame(summary_data)

        # Numeric stats sheet
        stats_rows = []
        for col in numeric_cols:
            stats_rows.append({
                "Column": col,
                "Count": int(df[col].count()),
                "Sum": round(float(df[col].sum()), 2),
                "Mean": round(float(df[col].mean()), 2),
                "Median": round(float(df[col].median()), 2),
                "Std": round(float(df[col].std()), 2),
                "Min": round(float(df[col].min()), 2),
                "Max": round(float(df[col].max()), 2),
            })
        stats_df = pd.DataFrame(stats_rows) if stats_rows else pd.DataFrame()

        # Category breakdown sheet
        cat_rows = []
        for col in categorical_cols:
            counts = df[col].value_counts().head(MAX_CATEGORY_VALUES)
            for value, count in counts.items():
                cat_rows.append({
                    "Column": col,
                    "Value": str(value),
                    "Count": int(count),
                    "Percentage": round(float(count / len(df) * 100), 2),
                })
        cat_df = pd.DataFrame(cat_rows) if cat_rows else pd.DataFrame()

        return {
            "raw_data": df,
            "summary": summary_df,
            "numeric_stats": stats_df,
            "category_breakdown": cat_df,
        }

    # ─── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _resolve_path(storage_key: str) -> Optional[Path]:
        """Resolve a storage key to a local path (supports both new keys and legacy absolute paths)."""
        storage = get_storage()
        local_path = storage.get_local_path(storage_key)
        if local_path:
            return local_path
        # Legacy absolute path fallback
        legacy = Path(storage_key)
        if legacy.is_absolute() and legacy.exists():
            return legacy
        return None

    @staticmethod
    def _get_numeric_columns(df: pd.DataFrame) -> list[str]:
        return [col for col in df.select_dtypes(include=[np.number]).columns]

    @staticmethod
    def _get_categorical_columns(df: pd.DataFrame) -> list[str]:
        result = []
        for col in df.columns:
            if df[col].dtype == object or str(df[col].dtype) in ("category", "str"):
                if df[col].nunique() <= MAX_CATEGORY_VALUES:
                    result.append(col)
        return result

    @staticmethod
    def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
        """Find the most likely date column by name pattern or dtype."""
        # First check actual datetime dtypes
        date_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns
        if len(date_cols) > 0:
            return date_cols[0]

        # Then check by name pattern
        for col in df.columns:
            col_lower = col.lower()
            if any(p in col_lower for p in DATE_PATTERNS):
                # Try to parse as date
                try:
                    pd.to_datetime(df[col].head(10))
                    return col
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _matches_pattern(col_name: str, patterns: tuple) -> bool:
        col_lower = col_name.lower().replace("_", "").replace(" ", "")
        return any(p in col_lower for p in patterns)

    def _compute_summary_kpis(self, df: pd.DataFrame, numeric_cols: list[str]) -> list[dict]:
        """Compute headline KPI numbers, prioritizing business-named columns."""
        kpis: list[dict] = []

        # Always include row count
        kpis.append({"name": "Total Records", "value": len(df), "type": "count"})

        # Find business-relevant columns and compute their totals
        for col in numeric_cols:
            if self._matches_pattern(col, REVENUE_PATTERNS):
                kpis.append({"name": f"Total {col}", "value": round(float(df[col].sum()), 2), "type": "currency"})
            elif self._matches_pattern(col, PROFIT_PATTERNS):
                kpis.append({"name": f"Total {col}", "value": round(float(df[col].sum()), 2), "type": "currency"})
            elif self._matches_pattern(col, QUANTITY_PATTERNS):
                kpis.append({"name": f"Total {col}", "value": round(float(df[col].sum()), 2), "type": "number"})
            elif self._matches_pattern(col, AMOUNT_PATTERNS):
                kpis.append({"name": f"Total {col}", "value": round(float(df[col].sum()), 2), "type": "currency"})

        # If no business-named columns found, use the first numeric columns
        if len(kpis) <= 1 and numeric_cols:
            for col in numeric_cols[:3]:
                kpis.append({"name": f"Sum of {col}", "value": round(float(df[col].sum()), 2), "type": "number"})
                kpis.append({"name": f"Avg {col}", "value": round(float(df[col].mean()), 2), "type": "number"})

        return kpis[:8]  # Cap at 8 headline KPIs

    @staticmethod
    def _compute_numeric_stats(df: pd.DataFrame, numeric_cols: list[str]) -> list[dict]:
        """Compute descriptive statistics for each numeric column."""
        stats = []
        for col in numeric_cols:
            series = df[col].dropna()
            if series.empty:
                continue
            stats.append({
                "column": col,
                "count": int(series.count()),
                "sum": round(float(series.sum()), 2),
                "mean": round(float(series.mean()), 2),
                "median": round(float(series.median()), 2),
                "std": round(float(series.std()), 2),
                "min": round(float(series.min()), 2),
                "max": round(float(series.max()), 2),
            })
        return stats

    @staticmethod
    def _compute_category_breakdowns(df: pd.DataFrame, categorical_cols: list[str]) -> list[dict]:
        """Compute value distributions for categorical columns."""
        breakdowns = []
        for col in categorical_cols:
            counts = df[col].value_counts().head(MAX_CATEGORY_VALUES)
            top_values = [
                {"value": str(val), "count": int(cnt), "percent": round(float(cnt / len(df) * 100), 1)}
                for val, cnt in counts.items()
            ]
            breakdowns.append({"column": col, "top_values": top_values})
        return breakdowns

    def _compute_time_trends(
        self, df: pd.DataFrame, numeric_cols: list[str], date_col: str
    ) -> list[dict]:
        """Compute monthly aggregates if a date column is detected."""
        try:
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col])

            if df.empty:
                return []

            df["_period"] = df[date_col].dt.to_period("M")
            grouped = df.groupby("_period")[numeric_cols].sum()

            trends = []
            for period, row in grouped.iterrows():
                metrics = {col: round(float(row[col]), 2) for col in numeric_cols if not pd.isna(row[col])}
                trends.append({"period": str(period), "metrics": metrics})

            return trends[-12:]  # Last 12 months max
        except Exception:
            return []
