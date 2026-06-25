# HarvestIQ Secondary Agronomic Algorithms & Mathematical Models

This document details the secondary rule engines and mathematical models used to evaluate historical trends, soil nutrients, yield risk, and overall farm health.

---

## 1. Stress Momentum Engine

This engine monitors how the Field Stress Index (FSI) changes over time. It compares the latest FSI score against the historical average of the preceding logs (up to 5 logs) to detect rapid spikes or drops before physical crop symptoms appear.

### Mathematical Formulation

$$\Delta = \text{FSI}_{\text{latest}} - \frac{\sum_{i=1}^{n-1} \text{FSI}_i}{n-1}$$

*   $\Delta$: Stress delta indicator (rate of change).
*   $\text{FSI}_{\text{latest}}$: The most recent calculated Field Stress Index.
*   $\text{FSI}_i$: Historical FSI values in the log array.
*   $n$: Total number of FSI logs available (minimum of 2 required).

### Trend Classifications

*   **RISING (Deteriorating Health):** $\Delta > 0.05$
*   **FALLING (Recovering Health):** $\Delta < -0.05$
*   **STABLE (Consistent State):** $-0.05 \le \Delta \le 0.05$

---

## 2. Soil Health Index (SHI) Engine

The SHI translates laboratory soil test measurements (NPK, pH, Organic Carbon, and Electrical Conductivity) into a single score out of 100 representing soil quality. The metrics are compared against crop-specific optimal reference bands.

### Mathematical Formulation

$$\text{SHI} = \frac{\sum (W_n \times S_n)}{\sum W_n} \times 100$$

*   $\text{SHI}$: Composite Soil Health Index (expressed as a score from 0 to 100).
*   $W_n$: Weight factor assigned to nutrient $n$ (Nitrogen = 0.35, Phosphorus = 0.20, Potassium = 0.15, pH = 0.15, Organic Carbon = 0.10, Electrical Conductivity = 0.05).
*   $S_n$: Individual nutrient score (clamped between 0.0 and 1.0) based on deviation from the crop's optimal reference range.

---

## 3. Explainable Yield Risk Engine

The Yield Risk Engine estimates overall danger to the harvest by evaluating weather stress, soil quality, crop age vulnerability, and pest/disease indicators.

### Mathematical Formulation

$$\text{Risk Percentage} = \text{clamp}\left(0.30 \times \text{FSI} + 0.15 \times \text{Momentum} + 0.15 \times \text{Vulnerability} + 0.20 \times \text{Soil-Stress} + 0.20 \times \text{Disease-Presence}\right) \times 100$$

*   $\text{FSI}$: Current Field Stress Index (0.0 to 1.0).
*   $\text{Momentum}$: Stress momentum score (representing the rate of deterioration).
*   $\text{Vulnerability}$: Growth stage vulnerability coefficient (e.g., higher during flowering/heading stages).
*   $\text{Soil-Stress}$: Computed as $1.0 - \text{SHI}$ (reflecting soil nutrient deficiency).
*   $\text{Disease-Presence}$: Flag indicating active localized leaf disease or nearby outbreak alerts (set to 1.0 if present, 0.0 if healthy).

### Risk Classification Bands

*   **LOW RISK:** $< 33\%$
*   **MEDIUM RISK:** $33\%$ to $66\%$
*   **HIGH RISK:** $\ge 66\%$

---

## 4. Unified Farm Health Score

The Unified Farm Health Score compiles all primary signals into a single score (out of 100) displayed on the main farmer dashboard.

### Mathematical Formulation

$$\text{Health Score} = S_{\text{fsi}} \times 25 + S_{\text{soil}} \times 25 + S_{\text{radar}} \times 10 + S_{\text{alerts}} \times 10 + S_{\text{yield-risk}} \times 10$$

*   $S_{\text{fsi}}$: Inverse FSI score, computed as $(1.0 - \text{FSI})$ scaled to 1.0.
*   $S_{\text{soil}}$: Normalized Soil Health Index (0.0 to 1.0).
*   $S_{\text{radar}}$: Region safety factor (1.0 if no nearby crop outbreaks are reported, 0.0 if high outbreaks exist).
*   $S_{\text{alerts}}$: Alert status weight (diminishes by 0.2 for every active unread warning alert, clamped to a minimum of 0.0).
*   $S_{\text{yield-risk}}$: Yield protection rating, computed as $1.0 - (\text{Risk Percentage} / 100.0)$.

### Rating Bands

*   **GOOD:** $\ge 75$
*   **FAIR:** $50$ to $74$
*   **POOR:** $< 50$
