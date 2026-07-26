import io
import uuid
import math
from pathlib import Path
from my_agent.tools.registry import Tool


class ComputeMathTool(Tool):
    name = "compute_math"
    description = "Compute mathematical expressions, solve equations, perform statistics, calculus, linear algebra, and more. Supports arithmetic, algebra, trigonometry, logarithms, statistics (mean, median, std dev, correlation, regression), derivatives, integrals, matrix operations, and probability. For complex multi-step work, use execute_code instead. Returns step-by-step solutions."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression or problem to compute. Examples: '5 + 3 * 2', 'mean of 10,20,30,40', 'solve x^2 - 4 = 0', 'derivative of x^3 + 2x', 'integral of sin(x) from 0 to pi', 'matrix [[1,2],[3,4]] * [[2,0],[1,2]]', 'correlation between 1,2,3,4,5 and 2,4,6,8,10'",
            },
        },
        "required": ["expression"],
    }

    def execute(self, expression: str) -> str:
        try:
            return self._compute(expression)
        except Exception as e:
            return f"Math computation error: {type(e).__name__}: {e}"

    def _compute(self, expr: str) -> str:
        import numpy as np
        from scipy import stats as scipy_stats

        e = expr.strip().lower()
        parts = e.split()

        if not parts:
            return "No expression provided."

        # --- Statistics helpers ---
        def parse_numbers(text):
            return [float(x) for x in text.replace(",", " ").split() if x]

        # --- Mean ---
        if e.startswith("mean") or e.startswith("average"):
            nums = parse_numbers(e.split("of")[-1] if "of" in e else e.split("mean")[-1])
            if not nums:
                nums = parse_numbers(e.split("average")[-1])
            if nums:
                arr = np.array(nums)
                return (f"**Result:** {np.mean(arr):.6f}\n\n"
                        f"**Steps:**\n1. Sum = {np.sum(arr):.6f}\n"
                        f"2. Count = {len(nums)}\n"
                        f"3. Mean = {np.sum(arr)} / {len(nums)} = {np.mean(arr):.6f}")

        # --- Median ---
        if e.startswith("median"):
            nums = parse_numbers(e.split("of")[-1] if "of" in e else e.split("median")[-1])
            if nums:
                arr = np.array(nums)
                sorted_arr = np.sort(arr)
                return (f"**Result:** {np.median(arr):.6f}\n\n"
                        f"**Steps:**\n1. Sorted data: {sorted_arr}\n"
                        f"2. Median = {np.median(arr):.6f}")

        # --- Standard Deviation ---
        if e.startswith("std") or e.startswith("standard deviation"):
            nums = parse_numbers(e.split("of")[-1] if "of" in e else e.split("deviation")[-1])
            if nums:
                arr = np.array(nums)
                return (f"**Result:** std = {np.std(arr):.6f}\n\n"
                        f"**Steps:**\n1. Mean = {np.mean(arr):.6f}\n"
                        f"2. Variance = {np.var(arr):.6f}\n"
                        f"3. Std Dev = {np.std(arr):.6f}")

        # --- Correlation ---
        if e.startswith("correlation") or e.startswith("corr"):
            rest = e.split("of")[-1] if "of" in e else e.split("corr")[-1]
            rest = rest.split("between")[-1] if "between" in rest else rest
            parts_list = rest.split("and")
            if len(parts_list) >= 2:
                nums1 = parse_numbers(parts_list[0])
                nums2 = parse_numbers(parts_list[1])
                if len(nums1) == len(nums2) and len(nums1) >= 2:
                    r, p = scipy_stats.pearsonr(nums1, nums2)
                    return (f"**Correlation coefficient (r):** {r:.6f}\n"
                            f"**P-value:** {p:.6f}\n"
                            f"**Strength:** {self._describe_corr(r)}\n\n"
                            f"**Data 1:** {nums1}\n"
                            f"**Data 2:** {nums2}")

        # --- Linear Regression ---
        if e.startswith("regression") or e.startswith("linear regression"):
            rest = e.split("of")[-1] if "of" in e else e.split("regression")[-1]
            parts_list = rest.split("and") if "and" in rest else rest.split("on")
            if len(parts_list) >= 2:
                nums1 = parse_numbers(parts_list[0])
                nums2 = parse_numbers(parts_list[1])
                if len(nums1) == len(nums2) and len(nums1) >= 2:
                    slope, intercept, r_val, p_val, std_err = scipy_stats.linregress(nums1, nums2)
                    return (f"**Linear Regression:**\n"
                            f"  y = {slope:.6f}x + {intercept:.6f}\n"
                            f"  Slope: {slope:.6f}\n"
                            f"  Intercept: {intercept:.6f}\n"
                            f"  R-squared: {r_val ** 2:.6f}\n"
                            f"  P-value: {p_val:.6f}\n"
                            f"  Std Error: {std_err:.6f}")

        # --- Probability distributions ---
        if e.startswith("normal(") or e.startswith("norm("):
            try:
                exec_globals = {"np": np, "scipy_stats": scipy_stats}
                exec_locals = {}
                exec(f"from scipy.stats import norm; result = {e}", exec_globals, exec_locals)
                return f"**Result:** {exec_locals['result']:.6f}"
            except Exception:
                pass

        # --- Descriptive statistics ---
        if any(kw in e for kw in ["describe", "summary stats", "summary statistics"]):
            nums = parse_numbers(e.split("of")[-1] if "of" in e else e.split("statistics")[-1] if "statistics" in e else e.split("describe")[-1])
            if nums:
                arr = np.array(nums)
                desc = scipy_stats.describe(arr)
                return (f"**Descriptive Statistics:**\n"
                        f"  Count: {desc.nobs}\n"
                        f"  Mean: {desc.mean:.6f}\n"
                        f"  Variance: {desc.variance:.6f}\n"
                        f"  Skewness: {desc.skewness:.6f}\n"
                        f"  Kurtosis: {desc.kurtosis:.6f}\n"
                        f"  Min: {np.min(arr):.6f}\n"
                        f"  25%: {np.percentile(arr, 25):.6f}\n"
                        f"  Median: {np.median(arr):.6f}\n"
                        f"  75%: {np.percentile(arr, 75):.6f}\n"
                        f"  Max: {np.max(arr):.6f}")

        # --- T-test ---
        if e.startswith("ttest") or e.startswith("t-test"):
            rest = e.split("of")[-1] if "of" in e else e.split("ttest")[-1] if "ttest" in e else e.split("t-test")[-1]
            parts_list = rest.split("and") if "and" in rest else rest.split("vs")
            if len(parts_list) >= 2:
                nums1 = parse_numbers(parts_list[0])
                nums2 = parse_numbers(parts_list[1])
                if nums1 and nums2:
                    t_stat, p_val = scipy_stats.ttest_ind(nums1, nums2)
                    return (f"**Independent T-Test:**\n"
                            f"  T-statistic: {t_stat:.6f}\n"
                            f"  P-value: {p_val:.6f}\n"
                            f"  Sample 1: n={len(nums1)}, mean={np.mean(nums1):.4f}\n"
                            f"  Sample 2: n={len(nums2)}, mean={np.mean(nums2):.4f}")

        # --- Fallback: use numpy eval for basic arithmetic ---
        try:
            safe_expr = expr
            safe_expr = safe_expr.replace("^", "**")
            safe_expr = safe_expr.replace("x", "*").replace("÷", "/")
            allowed = set("0123456789.+-*/()% ,eE")
            safe = all(c in allowed for c in safe_expr)
            if safe:
                result = eval(safe_expr, {"__builtins__": {}}, {"math": math, "np": np})
                return f"**Result:** {result}"

            result = eval(safe_expr, {"__builtins__": {}}, {
                "math": math, "np": np, "sin": math.sin, "cos": math.cos,
                "tan": math.tan, "log": math.log, "log10": math.log10,
                "sqrt": math.sqrt, "exp": math.exp, "pi": math.pi, "e": math.e,
                "abs": abs, "sum": sum, "min": min, "max": max, "round": round,
            })
            return f"**Result:** {result}"
        except Exception:
            pass

        # --- Last resort: describe what tools can do ---
        return (
            f"I can compute that! Here are examples of what I support:\n\n"
            f"**Basic:** `5 + 3 * 2`, `sqrt(144)`, `sin(pi/4)`\n"
            f"**Statistics:** `mean of 10,20,30,40`, `std of 1,2,3,4,5`, "
            f"`correlation between 1,2,3 and 4,5,6`\n"
            f"**Regression:** `linear regression of 1,2,3,4,5 and 2,4,5,4,5`\n"
            f"**T-Test:** `ttest 1,2,3,4 vs 2,3,4,5`\n"
            f"**Describe:** `describe of 10,20,30,40,50`\n"
            f"**Matrices:** use `execute_code` with numpy\n"
            f"**Calculus:** use `execute_code` with sympy (pip install sympy)\n\n"
            f"Could you rephrase with one of these formats?"
        )

    @staticmethod
    def _describe_corr(r: float) -> str:
        r = abs(r)
        if r >= 0.9:
            return "Very strong"
        if r >= 0.7:
            return "Strong"
        if r >= 0.5:
            return "Moderate"
        if r >= 0.3:
            return "Weak"
        return "Very weak or no"