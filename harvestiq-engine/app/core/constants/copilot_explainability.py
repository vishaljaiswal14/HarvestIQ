from typing import Final

# Templates: (why_key, if_ignored, expected_benefit) — filled with .format(**ctx)

EXPLAIN_DISEASE_CONFIRMED: Final[tuple[str, str, str]] = (
    "{disease_name} confirmed on latest scan",
    "Disease may spread across the field; significant crop damage possible within 7 days if untreated",
    "Timely treatment helps limit spread and supports potential loss prevention",
)

EXPLAIN_DISEASE_POSSIBLE: Final[tuple[str, str, str]] = (
    "Possible disease symptoms detected ({disease_name})",
    "Unconfirmed symptoms may develop into a full outbreak if not verified and treated",
    "Early verification and treatment reduce escalation risk",
)

EXPLAIN_FSI_HIGH: Final[tuple[str, str, str]] = (
    "Field stress index is elevated (FSI {fsi_pct}%) due to {primary_factor}",
    "Sustained stress can reduce crop vigor and increase vulnerability to pests and disease",
    "Prompt mitigation helps stabilize crop condition and supports loss prevention",
)

EXPLAIN_FSI_MEDIUM: Final[tuple[str, str, str]] = (
    "Moderate field stress detected (FSI {fsi_pct}%)",
    "Stress may intensify without monitoring and scheduled intervention",
    "Planned irrigation or monitoring prevents escalation to high stress",
)

EXPLAIN_RAINFALL_DEFICIT: Final[tuple[str, str, str]] = (
    "Rainfall deficit alert active during {stage} stage",
    "Moisture stress may affect grain fill and crop development",
    "Mulching or scheduled irrigation helps retain soil moisture",
)

EXPLAIN_THERMAL_HIGH: Final[tuple[str, str, str]] = (
    "High temperature alert active during {stage} stage",
    "Heat stress can reduce tillering and grain development",
    "Light irrigation or canopy cooling mitigates thermal damage",
)

EXPLAIN_HUMIDITY_RUST: Final[tuple[str, str, str]] = (
    "High humidity ({humidity}%) increases fungal disease risk for {crop}",
    "Favorable conditions for rust and fungal spread if not monitored",
    "Scouting and preventive measures reduce outbreak probability",
)

EXPLAIN_AUTO_SOS: Final[tuple[str, str, str]] = (
    "Critical farm alert: high FSI, confirmed disease, and elevated yield risk",
    "Severe conditions may lead to major crop loss without immediate emergency response",
    "Emergency dispatch alerts contacts and authorities for rapid assistance",
)

EXPLAIN_PREVENTIVE_SCOUTING: Final[tuple[str, str, str]] = (
    "Routine scouting recommended at {stage} stage for {crop}",
    "Early signs of stress or disease may go unnoticed until impact occurs",
    "Regular field checks enable low-cost early intervention",
)

EXPLAIN_ROUTINE_HEALTHY: Final[tuple[str, str, str]] = (
    "Farm conditions are within safe ranges (FSI {fsi_pct}%)",
    "Skipping routine checks may delay detection of emerging stress",
    "Continued monitoring maintains readiness for early action",
)

DEFAULT_IF_IGNORED: Final[str] = (
    "Delaying recommended action may allow conditions to worsen and increase potential crop loss"
)
DEFAULT_EXPECTED_BENEFIT: Final[str] = (
    "Taking action supports risk reduction and potential loss prevention"
)
