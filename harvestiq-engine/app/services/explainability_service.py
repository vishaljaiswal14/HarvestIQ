from typing import Any, Optional

_FACTOR_LABELS = {
    "en": {
        "THERMAL": "thermal stress",
        "MOISTURE": "rainfall deficit",
        "GDD": "growth stage vulnerability",
        "NITROGEN": "nitrogen deficiency",
        "PHOSPHORUS": "phosphorus deficiency",
        "POTASSIUM": "potassium deficiency",
        "PH": "soil pH imbalance",
        "ORGANIC_CARBON": "low organic carbon",
        "ELECTRICAL_CONDUCTIVITY": "salinity stress",
        "DISEASE": "disease detection",
    },
    "hi": {
        "THERMAL": "तापमान का तनाव",
        "MOISTURE": "वर्षा की कमी",
        "GDD": "फसल चक्र चरण संवेदनशीलता",
        "NITROGEN": "नाइट्रोजन की कमी",
        "PHOSPHORUS": "फास्फोरस की कमी",
        "POTASSIUM": "पोटेशियम की कमी",
        "PH": "मिट्टी के पीएच (pH) का असंतुलन",
        "ORGANIC_CARBON": "कम जैविक कार्बन",
        "ELECTRICAL_CONDUCTIVITY": "लवणता का तनाव (खारापन)",
        "DISEASE": "रोग का पता चलना",
    }
}

_CLASSIFICATION_LABELS = {
    "en": {
        "HIGH_STRESS": "High Stress",
        "MEDIUM_STRESS": "Medium Stress",
        "LOW_STRESS": "Low Stress",
        "NO_STRESS": "No Stress",
    },
    "hi": {
        "HIGH_STRESS": "उच्च तनाव",
        "MEDIUM_STRESS": "मध्यम तनाव",
        "LOW_STRESS": "कम तनाव",
        "NO_STRESS": "कोई तनाव नहीं",
    }
}

_NUTRIENT_LABELS = {
    "en": {
        "nitrogen": "nitrogen",
        "phosphorus": "phosphorus",
        "potassium": "potassium",
        "ph": "pH",
        "organic_carbon": "organic carbon",
        "electrical_conductivity": "electrical conductivity",
    },
    "hi": {
        "nitrogen": "नाइट्रोजन",
        "phosphorus": "फास्फोरस",
        "potassium": "पोटेशियम",
        "ph": "पीएच (pH)",
        "organic_carbon": "जैविक कार्बन",
        "electrical_conductivity": "विद्युत चालकता",
    }
}

_DISEASE_STATUS = {
    "en": {
        "CONFIRMED": "CONFIRMED",
        "UNCONFIRMED": "UNCONFIRMED",
        "SUSPECTED": "SUSPECTED",
    },
    "hi": {
        "CONFIRMED": "पुष्टि की गई",
        "UNCONFIRMED": "अपुष्ट",
        "SUSPECTED": "संदिग्ध",
    }
}

_SEVERITY_TIERS = {
    "en": {
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
        "NORMAL": "NORMAL",
    },
    "hi": {
        "CRITICAL": "क्रिटिकल (अत्यंत गंभीर)",
        "HIGH": "उच्च",
        "MEDIUM": "मध्यम",
        "LOW": "कम",
        "NORMAL": "सामान्य",
    }
}

_ACTION_TYPES = {
    "en": {
        "SPRAY": "Spray",
        "FERTILIZE": "Fertilize",
        "IRRIGATE": "Irrigate",
    },
    "hi": {
        "SPRAY": "छिड़काव (Spray)",
        "FERTILIZE": "उर्वरक (Fertilize)",
        "IRRIGATE": "सिंचाई (Irrigate)",
    }
}

_OPTIMIZER_STATUS = {
    "en": {
        "SAFE": "SAFE",
        "UNSAFE": "UNSAFE",
    },
    "hi": {
        "SAFE": "सुरक्षित",
        "UNSAFE": "असुरक्षित",
    }
}

_MOMENTUM_DIRECTIONS = {
    "en": {
        "UPWARD": "increasing",
        "DOWNWARD": "decreasing",
        "STABLE": "stable",
    },
    "hi": {
        "UPWARD": "बढ़ रहा है",
        "DOWNWARD": "घट रहा है",
        "STABLE": "स्थिर है",
    }
}

_RISK_BANDS = {
    "en": {
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
        "NONE": "NONE",
    },
    "hi": {
        "CRITICAL": "अत्यंत गंभीर (CRITICAL)",
        "HIGH": "उच्च (HIGH)",
        "MEDIUM": "मध्यम (MEDIUM)",
        "LOW": "कम (LOW)",
        "NONE": "कोई नहीं (NONE)",
    }
}


def build_fsi_explanation(
    fsi: float,
    classification: str,
    primary_factor: str,
    inputs: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    label = _FACTOR_LABELS[lang].get(primary_factor, primary_factor.lower())
    class_label = _CLASSIFICATION_LABELS[lang].get(classification, classification.replace("_", " ").title())
    
    if lang == "hi":
        summary = f"एफएसआई (FSI) {fsi} ({class_label}) है, जिसका मुख्य कारण {label} है।"
    else:
        summary = f"FSI is {fsi} ({class_label}) primarily due to {label}."
        
    return {
        "summary": summary,
        "inputs": inputs,
        "primary_factor": primary_factor,
    }


def build_soil_explanation(
    soil_health_index: float,
    primary_factor: str,
    inputs: dict[str, Any],
    deficiency_status: dict[str, str],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    label = _FACTOR_LABELS[lang].get(primary_factor, primary_factor.lower())
    low_nutrients = [k for k, v in deficiency_status.items() if v == "LOW"]
    translated_nutrients = [_NUTRIENT_LABELS[lang].get(n, n) for n in low_nutrients]
    
    if lang == "hi":
        summary = f"मिट्टी स्वास्थ्य सूचकांक {soil_health_index} है, और मुख्य चिंता: {label} है।"
        if translated_nutrients:
            summary += f" कम पोषक तत्व: {', '.join(translated_nutrients)}।"
    else:
        summary = f"Soil health index is {soil_health_index} with primary concern: {label}."
        if low_nutrients:
            summary += f" Low nutrients: {', '.join(low_nutrients)}."
            
    return {
        "summary": summary,
        "inputs": inputs,
        "primary_factor": primary_factor,
    }


def build_disease_explanation(
    disease: str,
    confidence: Optional[float],
    deterministic_status: str,
    primary_factor: str,
    inputs: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    conf_str = f"{confidence:.2f}" if confidence is not None else "N/A"
    
    status_label = _DISEASE_STATUS[lang].get(deterministic_status, deterministic_status)
    
    if lang == "hi":
        summary = f"विजन मॉडल ने {conf_str} आत्मविश्वास के साथ {disease} का सुझाव दिया। स्थिति: {status_label}।"
    else:
        summary = (
            f"Vision model suggested {disease} at {conf_str} confidence. "
            f"Deterministic status: {status_label}."
        )
        
    return {
        "summary": summary,
        "inputs": inputs,
        "primary_factor": primary_factor,
    }


def build_alert_severity_explanation(
    severity_tier: str,
    generated_because: list[str],
    critical_triggers: list[str],
    signals: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    severity_label = _SEVERITY_TIERS[lang].get(severity_tier, severity_tier)
    
    if lang == "hi":
        because_text = "; ".join(generated_because) if generated_because else "कोई सक्रिय जोखिम संकेत नहीं।"
        summary = (
            f"खेत की गंभीरता को {len(generated_because)} सक्रिय संकेत(संकेतों) के आधार पर "
            f"{severity_label} के रूप में वर्गीकृत किया गया है।"
        )
    else:
        because_text = "; ".join(generated_because) if generated_because else "No active risk signals."
        summary = (
            f"Farm severity classified as {severity_label} based on "
            f"{len(generated_because)} active signal(s)."
        )
        
    return {
        "summary": summary,
        "inputs": {
            "severity_tier": severity_tier,
            "generated_because": generated_because,
            "critical_triggers": critical_triggers,
            **signals,
        },
        "primary_factor": "SEVERITY",
        "because_text": because_text,
    }


def build_alert_explanation(
    rule_id: str,
    primary_factor: str,
    inputs: dict[str, Any],
    message: str,
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    if lang == "hi":
        summary = f"अलर्ट {rule_id} सक्रिय हुआ: {message}"
    else:
        summary = f"Alert {rule_id} triggered: {message}"
        
    return {
        "summary": summary,
        "inputs": inputs,
        "primary_factor": primary_factor,
    }


def build_advisory_explanation(
    primary_factor: str,
    inputs: dict[str, Any],
    triggered_rules: list[str],
    rag_sources: list[str],
    mitigation_locked: bool,
    nearby_outbreaks: list[str],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    if lang == "hi":
        parts = [f"परामर्श (Advisory) खेत की खुफिया जानकारी पर आधारित है (स्नैपशॉट {inputs.get('snapshot_version', 'v1')})।"]
        if triggered_rules:
            parts.append(f" सक्रिय नियम: {', '.join(triggered_rules)}।")
        if rag_sources:
            parts.append(f" ज्ञान स्रोत: {', '.join(rag_sources)}।")
        if nearby_outbreaks:
            parts.append(f" आसपास के प्रकोप: {', '.join(nearby_outbreaks)}।")
        if mitigation_locked:
            parts.append(" उच्च खेत तनाव के कारण शमन सलाह अवरुद्ध (locked) है।")
    else:
        parts = [f"Advisory grounded in deterministic farm intelligence (snapshot {inputs.get('snapshot_version', 'v1')})."]
        if triggered_rules:
            parts.append(f" Active rules: {', '.join(triggered_rules)}.")
        if rag_sources:
            parts.append(f" Knowledge sources: {', '.join(rag_sources)}.")
        if nearby_outbreaks:
            parts.append(f" Nearby outbreaks: {', '.join(nearby_outbreaks)}.")
        if mitigation_locked:
            parts.append(" Mitigation advice is locked due to high field stress.")
            
    enriched_inputs = {
        **inputs,
        "triggered_rules": triggered_rules,
        "rag_sources": rag_sources,
        "mitigation_locked": mitigation_locked,
        "nearby_outbreaks": nearby_outbreaks,
    }
    return {
        "summary": "".join(parts),
        "inputs": enriched_inputs,
        "primary_factor": primary_factor,
    }


def build_optimizer_explanation(
    action_type: str,
    safe: bool,
    reasons: list[str],
    triggered_rules: list[str],
    inputs: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    action_label = _ACTION_TYPES[lang].get(action_type, action_type)
    status_label = _OPTIMIZER_STATUS[lang].get("SAFE" if safe else "UNSAFE", "SAFE" if safe else "UNSAFE")
    
    if lang == "hi":
        summary = f"{action_label} के लिए इनपुट विंडो {status_label} है।"
        if triggered_rules:
            summary += f" नियम: {', '.join(triggered_rules)}।"
    else:
        status = "SAFE" if safe else "UNSAFE"
        summary = f"Input window for {action_type} is {status}."
        if triggered_rules:
            summary += f" Rules: {', '.join(triggered_rules)}."
            
    return {
        "summary": summary,
        "inputs": {**inputs, "triggered_rules": triggered_rules, "reasons": reasons},
        "primary_factor": action_type,
    }


def build_momentum_explanation(momentum: dict[str, Any], language: str = "en") -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    direction_raw = momentum.get("direction", "STABLE")
    direction_label = _MOMENTUM_DIRECTIONS[lang].get(direction_raw, direction_raw.lower())
    
    if lang == "hi":
        summary = (
            f"तनाव की गति {direction_label} है "
            f"(स्कोर={momentum.get('momentum_score')}, डेल्टा={momentum.get('fsi_delta')})।"
        )
    else:
        summary = (
            f"Stress momentum is {direction_label} "
            f"(score={momentum['momentum_score']}, delta={momentum['fsi_delta']})."
        )
        
    return {
        "summary": summary,
        "inputs": momentum,
        "primary_factor": "MOMENTUM",
    }


def build_yield_risk_explanation(yield_risk: dict[str, Any], language: str = "en") -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    risk_band_raw = yield_risk.get("risk_band", "NONE")
    risk_label = _RISK_BANDS[lang].get(risk_band_raw, risk_band_raw)
    factors = yield_risk.get("contributing_factors", [])
    
    if lang == "hi":
        summary = (
            f"उपज का जोखिम {yield_risk.get('estimated_risk_percent')}% पर {risk_label} है।"
        )
        if factors:
            summary += f" कारक: {', '.join(factors)}।"
    else:
        summary = (
            f"Yield risk is {risk_band_raw} "
            f"at {yield_risk['estimated_risk_percent']}%."
        )
        if factors:
            summary += f" Factors: {', '.join(factors)}."
            
    return {
        "summary": summary,
        "inputs": yield_risk,
        "primary_factor": "YIELD_RISK",
    }


def build_briefing_explanation(sections: dict[str, Any], language: str = "en") -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    if lang == "hi":
        summary = "दैनिक ब्रीफिंग खेत की खुफिया जानकारी स्नैपशॉट v3 से संकलित की गई है।"
    else:
        summary = "Daily briefing compiled from deterministic farm intelligence snapshot v3."
        
    return {
        "summary": summary,
        "inputs": sections,
        "primary_factor": "BRIEFING",
    }


def build_simulation_explanation(
    baseline_fsi: float,
    projected_fsi: float,
    inputs: dict[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    lang = language.lower() if language.lower() in ["en", "hi"] else "en"
    
    if lang == "hi":
        summary = (
            f"सिमुलेशन चयनित परिदृश्य के तहत एफएसआई (FSI) को {baseline_fsi} से {projected_fsi} "
            f"तक होने का अनुमान लगाता है।"
        )
    else:
        summary = (
            f"Simulation projects FSI from {baseline_fsi} to {projected_fsi} "
            f"under the selected scenario."
        )
        
    return {
        "summary": summary,
        "inputs": inputs,
        "primary_factor": "SIMULATION",
    }
