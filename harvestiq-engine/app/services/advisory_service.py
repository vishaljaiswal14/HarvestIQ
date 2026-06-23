from datetime import datetime, timezone
from typing import Optional, Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import bad_gateway, unprocessable_entity
from app.models.day5_schemas import AdvisoryAskRequest, AdvisoryAskResponse
from app.models.engine_schemas import ExplanationPayload
from app.services.context_compiler_service import ContextCompilerService
from app.services.input_window_optimizer_service import InputWindowOptimizerService
from app.models.day8_schemas_actions import AdvisoryActionsResponse, ActionCard
from app.integrations.gemini_client import OpenRouterClient


class AdvisoryService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        gemini_client: Optional[Any] = None,
    ) -> None:
        self.db = db
        self.context_compiler = ContextCompilerService(db)
        self.optimizer = InputWindowOptimizerService(db)
        self.gemini_client = gemini_client or OpenRouterClient()

    async def ask(self, user_id: str, payload: AdvisoryAskRequest, language: str) -> AdvisoryAskResponse:
        query = payload.query.strip()
        if not query:
            raise unprocessable_entity("Query is required")

        # Compile baseline context
        compiled = await self.context_compiler.compile_context(
            user_id=user_id,
            farm_id=payload.farm_id,
            query=query,
            language=language,
        )

        # Get core intelligence and weather details
        field_context = await self.context_compiler.stress_service.build_field_context(payload.farm_id, user_id)
        core = await self.context_compiler._build_core_intelligence(user_id, payload.farm_id)
        
        weather = field_context.weather
        
        # 1. Intent Classification (Bilingual Compound Intent Matching)
        query_lower = query.lower()
        matched_intents = []
        
        intent_keywords = {
            "IRRIGATION": ["irrigate", "water", "dry", "wilt", "watering", "सिंचाई", "पानी", "सूखा", "मुरझा", "नमी"],
            "FERTILIZER": ["fertilizer", "urea", "npk", "nitrogen", "potash", "phosphorus", "fertilize", "खाद", "यूरिया", "नाइट्रोजन", "मिट्टी"],
            "SPRAY": ["spray", "pest", "bug", "insecticide", "pesticide", "neem", "insect", "aphid", "छिड़काव", "कीटनाशक", "नीम", "कीट", "कीड़े"],
            "DISEASE": ["disease", "rust", "blight", "spots", "lesions", "mildew", "infection", "रोग", "बीमारी", "धब्बे", "गेरूआ", "पीला"],
            "WEATHER": ["weather", "forecast", "temp", "rain", "precipitation", "wind", "gdd", "मौसम", "तापमान", "बारिश", "हवा"],
            "MARKET": ["market", "mandi", "price", "rates", "modal", "sell", "मंडी", "भाव", "बाजार", "दाम"],
            "SCHEMES": ["scheme", "government", "yojana", "subsidy", "eligible", "योजना", "सब्सिडी", "सरकारी"],
            "YIELD_RISK": ["yield", "risk", "loss", "estimate", "उपज", "नुकसान", "जोखिम", "अनुमानित"],
            "HEALTH": ["health", "overall", "wellbeing", "status", "farm status", "आरोग्य", "स्वास्थ्य", "हाल", "स्थिति"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(kw in query_lower for kw in keywords):
                matched_intents.append(intent)
                
        if not matched_intents:
            matched_intents.append("HEALTH")

        # 2. Gather Recommendations and Evidence ("Why" blocks)
        synthesis_parts = []
        evidence_lines = []
        
        lang = language.lower() if language in ["hi", "en"] else "hi"

        # Check for active alerts
        unread_alerts = await self.context_compiler._count_unread_alerts(user_id, payload.farm_id)

        # Iterate matched intents
        for intent in matched_intents:
            if intent == "IRRIGATION":
                resp = await self.optimizer.evaluate(user_id, payload.farm_id, "IRRIGATE")
                forecast_rain = sum(day.precipitation for day in weather.forecast[:3])
                if lang == "hi":
                    status = "सुरक्षित है" if resp.safe else "असुरक्षित है"
                    synthesis_parts.append(f"सिंचाई सलाह: आपके खेत में अभी सिंचाई करना {status}।")
                    if resp.reasons:
                        synthesis_parts.append(f"सिंचाई न करने का कारण: {', '.join(resp.reasons)}।")
                    evidence_lines.append("• [सिंचाई] खेत का तनाव सूचकांक (FSI): " + str(core.fsi))
                    evidence_lines.append("• [सिंचाई] 3-दिवसीय वर्षा पूर्वानुमान: " + str(forecast_rain) + " मिमी")
                    evidence_lines.append("• [सिंचाई] सुरक्षित झरोखा स्थिति: " + ("हाँ" if resp.safe else "नहीं"))
                else:
                    status = "recommended" if resp.safe else "not recommended"
                    synthesis_parts.append(f"Irrigation Advisory: Watering is {status} for your field.")
                    if resp.reasons:
                        synthesis_parts.append(f"Irrigation restriction reasons: {', '.join(resp.reasons)}.")
                    evidence_lines.append(f"• [Irrigation] Field Stress Index (FSI): {core.fsi}")
                    evidence_lines.append(f"• [Irrigation] 3-day precipitation forecast: {forecast_rain} mm")
                    evidence_lines.append(f"• [Irrigation] Safety window status: {'Safe' if resp.safe else 'Unsafe'}")

            elif intent == "FERTILIZER":
                resp = await self.optimizer.evaluate(user_id, payload.farm_id, "FERTILIZE")
                soil_section, soil_data = await self.context_compiler._build_soil_section(payload.farm_id)
                n_status = "OPTIMAL"
                p_status = "OPTIMAL"
                k_status = "OPTIMAL"
                shi = 100.0
                
                if soil_data:
                    deficiency = soil_data.get("deficiency_status", {})
                    n_status = deficiency.get("nitrogen", "OPTIMAL")
                    p_status = deficiency.get("phosphorus", "OPTIMAL")
                    k_status = deficiency.get("potassium", "OPTIMAL")
                    shi = soil_data.get("soil_health_index", 100.0)
                
                if lang == "hi":
                    status = "सुरक्षित है" if resp.safe else "असुरक्षित है"
                    synthesis_parts.append(f"खाद सलाह: उर्वरक/खाद डालना अभी {status}।")
                    if n_status == "DEFICIENT":
                        synthesis_parts.append("नाइट्रोजन (N) की कमी पाई गई है; यूरिया डालने पर विचार करें।")
                    if p_status == "DEFICIENT":
                        synthesis_parts.append("फॉस्फोरस (P) की कमी पाई गई है; डीएपी (DAP) का प्रयोग करें।")
                    if k_status == "DEFICIENT":
                        synthesis_parts.append("पोटेशियम (K) की कमी पाई गई है; एमओपी (MOP) का छिड़काव करें।")
                    if n_status != "DEFICIENT" and p_status != "DEFICIENT" and k_status != "DEFICIENT":
                        synthesis_parts.append("सभी मुख्य मिट्टी पोषक तत्व पर्याप्त स्तर पर हैं।")
                        
                    evidence_lines.append("• [उर्वरक] मिट्टी स्वास्थ्य सूचकांक: " + str(shi))
                    evidence_lines.append(f"• [उर्वरक] एनपीके स्थिति: N={n_status}, P={p_status}, K={k_status}")
                    evidence_lines.append("• [उर्वरक] सुरक्षा विंडो: " + ("हाँ" if resp.safe else "नहीं"))
                else:
                    status = "recommended" if resp.safe else "not recommended"
                    synthesis_parts.append(f"Fertilizer Advisory: Fertilizer application is {status}.")
                    if n_status == "DEFICIENT":
                        synthesis_parts.append("Nitrogen deficiency detected; urea application is recommended.")
                    if p_status == "DEFICIENT":
                        synthesis_parts.append("Phosphorus deficiency detected; consider applying DAP.")
                    if k_status == "DEFICIENT":
                        synthesis_parts.append("Potassium deficiency detected; consider applying MOP.")
                    if n_status != "DEFICIENT" and p_status != "DEFICIENT" and k_status != "DEFICIENT":
                        synthesis_parts.append("All key soil macronutrients are within optimal ranges.")
                        
                    evidence_lines.append(f"• [Fertilizer] Soil Health Index: {shi}")
                    evidence_lines.append(f"• [Fertilizer] NPK Status: N={n_status}, P={p_status}, K={k_status}")
                    evidence_lines.append(f"• [Fertilizer] Application window: {'Safe' if resp.safe else 'Unsafe'}")

            elif intent == "SPRAY":
                resp = await self.optimizer.evaluate(user_id, payload.farm_id, "SPRAY")
                if lang == "hi":
                    status = "अनुकूल है" if resp.safe else "अनुकूल नहीं है"
                    synthesis_parts.append(f"छिड़काव सलाह: दवाओं/कीटनाशकों के छिड़काव के लिए मौसम {status}।")
                    if resp.reasons:
                        synthesis_parts.append(f"कारण: {', '.join(resp.reasons)}।")
                    evidence_lines.append("• [छिड़काव] वर्तमान हवा की गति: " + str(weather.current.wind_speed) + " किमी/घंटा")
                    evidence_lines.append("• [छिड़काव] छिड़काव सुरक्षा विंडो: " + ("हाँ" if resp.safe else "नहीं"))
                else:
                    status = "safe" if resp.safe else "unsafe"
                    synthesis_parts.append(f"Spray Advisory: Current conditions are {status} for chemical applications.")
                    if resp.reasons:
                        synthesis_parts.append(f"Details: {', '.join(resp.reasons)}.")
                    evidence_lines.append(f"• [Spray] Wind Speed: {weather.current.wind_speed} km/h")
                    evidence_lines.append(f"• [Spray] Safety status: {'Safe' if resp.safe else 'Unsafe'}")

            elif intent == "DISEASE":
                disease_present = core.disease_present
                radar_high_nearby, radar_high_count = await self.context_compiler._radar_high_nearby(user_id, payload.farm_id, core.crop_type)
                
                # Fetch recent confirmed disease
                cursor = self.db.disease_reports.find({"farm_id": ObjectId(payload.farm_id)}).sort("created_at", -1).limit(1)
                latest_report = None
                async for r in cursor:
                    latest_report = r
                
                disease_name = "सक्रिय रोग" if lang == "hi" else "active disease"
                if latest_report:
                    disease_name = latest_report.get("detected_disease", disease_name)
                
                if lang == "hi":
                    if disease_present:
                        synthesis_parts.append(f"रोग चेतावनी: खेत में {disease_name} संक्रमण की पुष्टि हुई है।")
                    else:
                        synthesis_parts.append("रोग स्थिति: खेत में वर्तमान में कोई सक्रिय संक्रमण नहीं पाया गया है।")
                    if radar_high_nearby:
                        synthesis_parts.append(f"रडार चेतावनी: आस-पास के क्षेत्रों में {radar_high_count} उच्च-जोखिम हॉटस्पॉट सक्रिय हैं।")
                    evidence_lines.append("• [रोग] संक्रमण सक्रिय: " + ("हाँ" if disease_present else "नहीं"))
                    evidence_lines.append("• [रोग] निकटतम उच्च-जोखिम हॉटस्पॉट: " + str(radar_high_count))
                else:
                    if disease_present:
                        synthesis_parts.append(f"Disease Warning: Active infection of {disease_name} is confirmed on the farm.")
                    else:
                        synthesis_parts.append("Disease Status: No active disease infection detected on your farm.")
                    if radar_high_nearby:
                        synthesis_parts.append(f"Radar Alert: {radar_high_count} high-risk disease outbreaks reported nearby.")
                    evidence_lines.append(f"• [Disease] Active infection: {'Yes' if disease_present else 'No'}")
                    evidence_lines.append(f"• [Disease] High-risk nearby outbreaks: {radar_high_count}")

            elif intent == "WEATHER":
                if lang == "hi":
                    synthesis_parts.append(f"मौसम विवरण: वर्तमान तापमान {weather.current.temp}°C और आर्द्रता {weather.current.humidity}% है।")
                    evidence_lines.append("• [मौसम] हवा की गति: " + str(weather.current.wind_speed) + " किमी/घंटा")
                    evidence_lines.append("• [मौसम] संचित जीडीडी (GDD): " + str(core.current_gdd))
                else:
                    synthesis_parts.append(f"Weather Outlook: Current temperature is {weather.current.temp}°C with humidity at {weather.current.humidity}%.")
                    evidence_lines.append(f"• [Weather] Wind speed: {weather.current.wind_speed} km/h")
                    evidence_lines.append(f"• [Weather] Accumulated GDD: {core.current_gdd}")

            elif intent == "MARKET":
                market_summary = await self.context_compiler.market_service.get_summary_for_farm(user_id, payload.farm_id)
                if lang == "hi":
                    if market_summary:
                        synthesis_parts.append(f"बाज़ार मूल्य: {market_summary.get('crop_type', core.crop_type)} का मॉडल मूल्य मण्डी {market_summary.get('mandi', 'स्थानीय')} में ₹{market_summary.get('modal_price')}/क्विंटल है। रुझान: {market_summary.get('trend', 'स्थिर')}।")
                    else:
                        synthesis_parts.append("बाज़ार विवरण: अभी मंडी मूल्य विवरण उपलब्ध नहीं है।")
                    evidence_lines.append("• [मंडी] मंडी स्रोत: " + (market_summary.get('mandi') if market_summary else "अनुपलब्ध"))
                else:
                    if market_summary:
                        synthesis_parts.append(f"Market Prices: Modal price for {market_summary.get('crop_type', core.crop_type)} at {market_summary.get('mandi', 'Local')} is ₹{market_summary.get('modal_price')}/quintal. Trend is {market_summary.get('trend', 'STABLE')}.")
                    else:
                        synthesis_parts.append("Market Prices: Mandi price trend data is currently unavailable.")
                    evidence_lines.append(f"• [Market] Mandi Source: {market_summary.get('mandi') if market_summary else 'N/A'}")

            elif intent == "SCHEMES":
                schemes_data = await self.context_compiler.scheme_service.get_eligible(user_id, payload.farm_id)
                count = len(schemes_data.schemes) if schemes_data else 0
                if lang == "hi":
                    synthesis_parts.append(f"कृषि योजनाएं: आप {count} सरकारी सहायता/सब्सिडी योजनाओं के लिए पात्र हैं।")
                    if count > 0:
                        synthesis_parts.append(f"अनुशंसित: {schemes_data.schemes[0].name}।")
                    evidence_lines.append("• [योजनाएं] कुल पात्र सरकारी योजनाएं: " + str(count))
                else:
                    synthesis_parts.append(f"Government Schemes: You are eligible for {count} government schemes.")
                    if count > 0:
                        synthesis_parts.append(f"Recommended scheme: {schemes_data.schemes[0].name}.")
                    evidence_lines.append(f"• [Schemes] Eligible matched schemes: {count}")

            elif intent == "YIELD_RISK":
                pct = core.yield_risk.estimated_risk_percent
                band = core.yield_risk.risk_band
                factors = ", ".join(core.yield_risk.contributing_factors)
                if lang == "hi":
                    synthesis_parts.append(f"उपज जोखिम: आपके वर्तमान चक्र में जोखिम का स्तर '{band}' है। संभावित नुकसान का अनुमान {pct}% है।")
                    evidence_lines.append("• [जोखिम] मुख्य योगदान कारक: " + factors)
                else:
                    synthesis_parts.append(f"Yield Risk: Yield risk level is currently classified as '{band}' with a projected loss of {pct}%.")
                    evidence_lines.append(f"• [Risk] Key contributing factors: {factors}")

            elif intent == "HEALTH":
                health_snapshot = await self.context_compiler.compile_health_snapshot(user_id, payload.farm_id, language=language)
                band = health_snapshot.health_band
                score = health_snapshot.health_score
                if lang == "hi":
                    synthesis_parts.append(f"खेत स्वास्थ्य: आपके खेत का समग्र स्वास्थ्य वर्गीकरण '{band}' है (स्वास्थ्य स्कोर: {score}/100)।")
                    evidence_lines.append("• [स्वास्थ्य] सक्रिय अपठित चेतावनियां: " + str(unread_alerts))
                    evidence_lines.append("• [स्वास्थ्य] क्षेत्र तनाव सूचकांक (FSI): " + str(core.fsi))
                else:
                    synthesis_parts.append(f"Farm Health: Overall farm health status is classified as '{band}' (health score: {score}/100).")
                    evidence_lines.append(f"• [Health] Active unread alerts: {unread_alerts}")
                    evidence_lines.append(f"• [Health] Field Stress Index (FSI): {core.fsi}")

        # Combine synthesis parts and evidence
        local_synthesis = " ".join(synthesis_parts)
        if evidence_lines:
            why_header = "\n\nWhy / साक्ष्य:\n" if lang == "hi" else "\n\nWhy / Evidence:\n"
            local_synthesis += why_header + "\n".join(evidence_lines)

        synthesis = None
        if self.gemini_client and self.gemini_client.api_key:
            try:
                synthesis = await self.gemini_client.synthesize_advisory(
                    context_package=compiled.context_package,
                    language=language,
                    mitigation_locked=compiled.mitigation_locked,
                )
            except Exception as exc:
                print(f"Gemini synthesize_advisory failed: {exc}. Falling back to local synthesis.", flush=True)
                synthesis = local_synthesis
        else:
            synthesis = local_synthesis

        if not synthesis:
            synthesis = local_synthesis

        # 3. Compute Categorical Confidence (HIGH / MEDIUM / LOW)
        if core.soil_health_index is not None and unread_alerts <= 2:
            confidence = "HIGH"
        elif core.soil_health_index is not None:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # 4. Persistence Logging
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(payload.farm_id),
            "query": query,
            "language": language,
            "context_package": compiled.context_package,
            "context_hash": compiled.context_hash,
            "synthesis": synthesis,
            "citations": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in compiled.citations] if compiled.citations else [],
            "explainability": {
                "summary": f"Deterministic rule resolution (Matched: {', '.join(matched_intents)}).",
                "inputs": {
                    **compiled.explainability.get("inputs", {}),
                    "confidence_level": confidence,
                    "matched_intents": matched_intents,
                },
                "primary_factor": core.primary_factor,
            },
            "rag_chunk_ids": compiled.rag_chunk_ids,
            "intelligence_snapshot_version": compiled.intelligence_snapshot_version,
            "created_at": now,
        }
        result = await self.db.advisory_logs.insert_one(doc)

        return AdvisoryAskResponse(
            advisory_id=str(result.inserted_id),
            farm_id=payload.farm_id,
            synthesis=synthesis,
            advisory_text=synthesis,
            language=language,
            explainability=ExplanationPayload(
                summary=doc["explainability"]["summary"],
                inputs=doc["explainability"]["inputs"],
                primary_factor=doc["explainability"]["primary_factor"]
            ),
            explanation=doc["explainability"],
            citations=compiled.citations,
            intelligence_snapshot_version=compiled.intelligence_snapshot_version,
        )

    async def get_actions(self, user_id: str, farm_id: str, language: str) -> AdvisoryActionsResponse:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")

        # 1. Build core intelligence and field context
        core = await self.context_compiler._build_core_intelligence(user_id, farm_id)
        field_context = await self.context_compiler.stress_service.build_field_context(farm_id, user_id)
        weather = field_context.weather
        
        # 2. Query latest disease report
        latest_disease = await self.db.disease_reports.find_one(
            {"farm_id": ObjectId(farm_id)},
            sort=[("created_at", -1)]
        )

        # 3. Fetch active unread alerts
        alerts_cursor = self.db.alerts.find({"farm_id": ObjectId(farm_id), "read": False})
        active_alerts = [doc async for doc in alerts_cursor]

        # Inputs for recommendation
        fsi = core.fsi
        crop = core.crop_type
        stage = core.stage
        humidity = weather.current.humidity
        
        lang = language.lower() if language in ["hi", "en", "mr"] else "hi"

        priority = "LOW"
        situation_summary = ""
        today_actions = []
        this_week_actions = []
        why_generated = []
        potential_yield_reduction = 0

        # Disease Rule Checks
        has_disease_outbreak = False
        disease_tag = "UNKNOWN"
        disease_name = "Disease"
        if latest_disease:
            status = latest_disease.get("deterministic_status", "UNKNOWN").upper()
            if status in ["POSSIBLE_DISEASE", "CONFIRMED_DISEASE"]:
                has_disease_outbreak = True
                disease_tag = latest_disease.get("disease", "UNKNOWN")
                disease_name = latest_disease.get("disease_name") or latest_disease.get("disease") or "Wheat Rust"

        # Localization translations
        is_auto_sos = False
        if fsi > 0.80 and core.disease_present and core.yield_risk.estimated_risk_percent > 60.0:
            is_auto_sos = True

        if lang == "hi":
            # Situations
            if is_auto_sos:
                priority = "EMERGENCY"
                situation_summary = "आपके खेत में गंभीर अलर्ट स्थिति उत्पन्न हो गई है! FSI 80% से अधिक है, फसल में बीमारी की पुष्टि हुई है और उपज का अनुमानित जोखिम 60% से अधिक है। कृपया तुरंत आपातकालीन सहायता के लिए वन-क्लिक SOS का उपयोग करें।"
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem="गंभीर खेत चेतावनी का पता चला है (Critical Farm Alert Detected)",
                    action="एक-क्लिक आपातकालीन SOS भेजें (One-click Emergency SOS Dispatch)",
                    deadline="तुरंत (Immediate)",
                    expected_impact="आसपास के अधिकारियों और संपर्कों को सचेत करें (Alert nearby authorities and contacts)",
                    is_sos=True
                ))
                why_generated.append("Critical Farm Alert criteria met")
                potential_yield_reduction += 25
            elif has_disease_outbreak:
                priority = "HIGH"
                situation_summary = f"आपकी {crop} की फसल में {disease_name} के लक्षण दिखाई दे रहे हैं। जोखिम का स्तर: उच्च। फसल के नुकसान से बचने के लिए 48 घंटों के भीतर कार्रवाई करें।"
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem=f"{disease_name} संक्रमण का पता चला है।",
                    action=f"तुरंत अनुशंसित कवकनाशी (जैसे प्रोपिकोनाज़ोल) या उपचार का छिड़काव करें।",
                    deadline="48 घंटे के भीतर",
                    expected_impact="रोग के प्रसार को रोकें और उपज की रक्षा करें।"
                ))
                why_generated.append(f"{disease_name} का पता चला")
                potential_yield_reduction += 15  # 10-20% range mid
            
            if fsi >= 0.65:
                if priority != "EMERGENCY":
                    priority = "HIGH"
                if not situation_summary:
                    situation_summary = f"आपकी {crop} की फसल {core.primary_factor} तनाव के कारण अत्यधिक दबाव (FSI: {int(fsi * 100)}%) में है। अपनी उपज बचाने के लिए तुरंत कार्रवाई करें।"
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem=f"अत्यधिक खेत तनाव (FSI: {int(fsi * 100)}%) {core.primary_factor} कारकों के कारण है।",
                    action="मिट्टी की नमी बहाल करने के लिए तुरंत सिंचाई करें।" if core.primary_factor == "MOISTURE" else "तापमान के प्रभाव को कम करने के लिए हल्की सिंचाई या मल्चिंग का उपयोग करें।",
                    deadline="24 घंटे के भीतर",
                    expected_impact="फसल के स्वास्थ्य को स्थिर करें और उपज के गंभीर नुकसान से बचाएं।"
                ))
                why_generated.append(f"FSI = {int(fsi * 100)}%")
                potential_yield_reduction += 8  # 5-10% range mid
            elif 0.35 <= fsi < 0.65:
                if priority != "HIGH":
                    priority = "MEDIUM"
                if not situation_summary:
                    situation_summary = f"आपकी {crop} की फसल में मध्यम तनाव (FSI: {int(fsi * 100)}%) देखा गया है। सुरक्षा सुनिश्चित करने के लिए निगरानी जारी रखें।"
                this_week_actions.append(ActionCard(
                    card_type="YELLOW",
                    problem=f"मध्यम खेत तनाव (FSI: {int(fsi * 100)}%) है।",
                    action="दैनिक मिट्टी की नमी की जांच करें और अगले 2-3 दिनों में सिंचाई की योजना बनाएं।",
                    deadline="इस सप्ताह",
                    expected_impact="फसल को अत्यधिक तनाव में जाने से रोकना।"
                ))
                why_generated.append(f"FSI = {int(fsi * 100)}%")
                potential_yield_reduction += 3
            
            # Alerts Rules
            for alert in active_alerts:
                rule_id = alert.get("rule_id", "")
                if rule_id == "RULE_RAINFALL_DEFICIT":
                    if priority != "HIGH":
                        priority = "MEDIUM"
                    this_week_actions.append(ActionCard(
                        card_type="YELLOW",
                        problem="खेत में वर्षा की कमी (Rainfall Deficit) की चेतावनी सक्रिय है।",
                        action="नमी के संरक्षण के लिए पुआल मल्चिंग लगाएं या हल्की सिंचाई की योजना बनाएं।",
                        deadline="इस सप्ताह",
                        expected_impact="मिट्टी की नमी के वाष्पीकरण को कम करें।"
                    ))
                    why_generated.append("Rainfall deficit alert active")
                elif rule_id == "RULE_THERMAL_HIGH":
                    if priority != "HIGH":
                        priority = "MEDIUM"
                    this_week_actions.append(ActionCard(
                        card_type="YELLOW",
                        problem="उच्च तापमान चेतावनी (High Thermal Stress) सक्रिय है।",
                        action="दोपहर के समय पत्तों के मुरझाने की जांच करें और हल्की सिंचाई प्रदान करें।",
                        deadline="इस सप्ताह",
                        expected_impact="फसल को गर्मी की लहर (Heat Wave) से बचाएं।"
                    ))
                    why_generated.append("High thermal stress alert active")

            # Humidity Check
            if humidity > 80.0 and crop.upper() == "WHEAT":
                if priority != "HIGH":
                    priority = "MEDIUM"
                this_week_actions.append(ActionCard(
                    card_type="YELLOW",
                    problem=f"उच्च सापेक्ष आर्द्रता ({int(humidity)}%) देखी गई है। कवक रोग का जोखिम।",
                    action="खेत में अत्यधिक पानी जमा होने से बचें और जंग (Rust) के लक्षणों के लिए पत्तियों की बारीकी से जांच करें।",
                    deadline="इस सप्ताह",
                    expected_impact="बीमारी के अनुकूल सूक्ष्म जलवायु को कम करना।"
                ))
                why_generated.append(f"Humidity above threshold ({int(humidity)}%)")

            # Fallback Healthy
            if not today_actions and not this_week_actions:
                priority = "LOW"
                situation_summary = f"आपके खेत की स्थिति अनुकूल है। कोई सक्रिय जोखिम या तनाव के लक्षण नहीं पाए गए हैं।"
                this_week_actions.append(ActionCard(
                    card_type="GREEN",
                    problem="नियमित जांच",
                    action="दैनिक मौसम पूर्वानुमान देखें और सामान्य निगरानी जारी रखें।",
                    deadline="इस सप्ताह",
                    expected_impact="फसल के स्वस्थ विकास चक्र को बनाए रखें।"
                ))
                why_generated.extend([f"FSI = {int(fsi * 100)}% (सुरक्षित सीमा)", "कोई सक्रिय रोग नहीं मिला"])
                ignore_risk = "कोई तत्काल उपज जोखिम नहीं। नियमित जांच की अनदेखी करने से शुरुआती तनाव का पता लगाने में देरी हो सकती है।"
            else:
                # Calculate ignore consequence text based on gathered rates
                if potential_yield_reduction >= 20:
                    ignore_risk = f"यदि 5-7 दिनों तक अनदेखा किया गया:\nसंभावित उपज में कमी: 15-25%"
                elif potential_yield_reduction >= 12:
                    ignore_risk = f"यदि 5-7 दिनों तक अनदेखा किया गया:\nसंभावित उपज में कमी: 10-20%"
                elif potential_yield_reduction >= 5:
                    ignore_risk = f"यदि 5-7 दिनों तक अनदेखा किया गया:\nसंभावित उपज में कमी: 5-10%"
                else:
                    ignore_risk = f"यदि 5-7 दिनों तक अनदेखा किया गया:\nसंभावित उपज में कमी: 2-5%"

        else:  # en/mr defaults to en for actions presentation
            if is_auto_sos:
                priority = "EMERGENCY"
                situation_summary = "Critical Alert condition detected on your farm! FSI is above 80%, disease has been confirmed, and estimated yield risk is greater than 60%. Please use one-click dispatch to alert emergency contacts."
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem="Critical Farm Alert Detected",
                    action="One-click Emergency SOS Dispatch",
                    deadline="Immediate",
                    expected_impact="Alert nearby authorities and contacts",
                    is_sos=True
                ))
                why_generated.append("Critical Farm Alert criteria met")
                potential_yield_reduction += 25
            elif has_disease_outbreak:
                priority = "HIGH"
                situation_summary = f"Your {crop.title()} crop is showing signs of {disease_name}. Risk Level: High. Take action within 48 hours to avoid yield loss."
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem=f"{disease_name} infection detected.",
                    action=f"Spray recommended fungicide (e.g. Propiconazole) or treatment immediately.",
                    deadline="Within 48 hours",
                    expected_impact="Halt disease spread and protect yield."
                ))
                why_generated.append(f"{disease_name} detected")
                potential_yield_reduction += 15

            if fsi >= 0.65:
                if priority != "EMERGENCY":
                    priority = "HIGH"
                if not situation_summary:
                    situation_summary = f"Your {crop.title()} crop is undergoing high stress due to {core.primary_factor} deficit/excess (FSI: {int(fsi * 100)}%). Act now to save your yield."
                today_actions.append(ActionCard(
                    card_type="RED",
                    problem=f"High field stress (FSI: {int(fsi * 100)}%) due to {core.primary_factor} factors.",
                    action="Irrigate your farm immediately to restore soil moisture." if core.primary_factor == "MOISTURE" else "Apply light watering or canopy shading to mitigate thermal stress.",
                    deadline="Within 24 hours",
                    expected_impact="Stabilize crop health and prevent severe yield damage."
                ))
                why_generated.append(f"FSI = {int(fsi * 100)}%")
                potential_yield_reduction += 8
            elif 0.35 <= fsi < 0.65:
                if priority != "HIGH":
                    priority = "MEDIUM"
                if not situation_summary:
                    situation_summary = f"Your {crop.title()} crop is showing moderate stress (FSI: {int(fsi * 100)}%). Monitor closely and schedule operations."
                this_week_actions.append(ActionCard(
                    card_type="YELLOW",
                    problem=f"Moderate moisture/thermal stress (FSI: {int(fsi * 100)}%).",
                    action="Monitor soil moisture levels daily and plan irrigation over the next 2-3 days.",
                    deadline="This week",
                    expected_impact="Prevent crop from shifting into high stress bounds."
                ))
                why_generated.append(f"FSI = {int(fsi * 100)}%")
                potential_yield_reduction += 3

            # Alerts Rules
            for alert in active_alerts:
                rule_id = alert.get("rule_id", "")
                if rule_id == "RULE_RAINFALL_DEFICIT":
                    if priority != "HIGH":
                        priority = "MEDIUM"
                    this_week_actions.append(ActionCard(
                        card_type="YELLOW",
                        problem="Rainfall deficit alert is currently active for your region.",
                        action="Apply straw mulch to conserve soil moisture or plan light irrigation.",
                        deadline="This week",
                        expected_impact="Conserve soil moisture and protect crop root zone from drying."
                    ))
                    why_generated.append("Rainfall deficit alert active")
                elif rule_id == "RULE_THERMAL_HIGH":
                    if priority != "HIGH":
                        priority = "MEDIUM"
                    this_week_actions.append(ActionCard(
                        card_type="YELLOW",
                        problem="High thermal stress alert is active.",
                        action="Check crop leaves for midday wilting and irrigate if necessary.",
                        deadline="This week",
                        expected_impact="Reduce heat-induced transpiration stress."
                    ))
                    why_generated.append("High thermal stress alert active")

            # Humidity Check
            if humidity > 80.0 and crop.upper() == "WHEAT":
                if priority != "HIGH":
                    priority = "MEDIUM"
                this_week_actions.append(ActionCard(
                    card_type="YELLOW",
                    problem=f"High relative humidity ({int(humidity)}%) detected. High risk of fungal infections.",
                    action="Avoid over-watering and monitor crop leaves daily for rust spots.",
                    deadline="This week",
                    expected_impact="Minimize microclimate moisture favoring rust spore growth."
                ))
                why_generated.append(f"Humidity above threshold ({int(humidity)}%)")

            # Fallback Healthy
            if not today_actions and not this_week_actions:
                priority = "LOW"
                situation_summary = f"Your farm conditions are optimal. No active risks or stress signs detected."
                this_week_actions.append(ActionCard(
                    card_type="GREEN",
                    problem="Routine Checks",
                    action="Continue routine monitoring, check weather forecasts, and keep record entries updated.",
                    deadline="This week",
                    expected_impact="Maintain healthy crop growth stage transitions."
                ))
                why_generated.extend([f"FSI = {int(fsi * 100)}% (safe bounds)", "No active diseases detected"])
                ignore_risk = "No immediate yield risks. Ignoring routine checks may delay detection of early stress."
            else:
                if potential_yield_reduction >= 20:
                    ignore_risk = f"If ignored for 5-7 days:\nPotential yield reduction: 15-25%"
                elif potential_yield_reduction >= 12:
                    ignore_risk = f"If ignored for 5-7 days:\nPotential yield reduction: 10-20%"
                elif potential_yield_reduction >= 5:
                    ignore_risk = f"If ignored for 5-7 days:\nPotential yield reduction: 5-10%"
                else:
                    ignore_risk = f"If ignored for 5-7 days:\nPotential yield reduction: 2-5%"

        return AdvisoryActionsResponse(
            priority=priority,
            situation_summary=situation_summary,
            today_actions=today_actions,
            this_week_actions=this_week_actions,
            ignore_risk=ignore_risk,
            why_generated=why_generated
        )
