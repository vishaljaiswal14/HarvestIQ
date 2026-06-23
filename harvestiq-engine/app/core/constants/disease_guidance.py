from typing import Dict, List, Any

DISEASE_GUIDANCE: Dict[str, Dict[str, Any]] = {
    "WHEAT_RUST": {
        "disease_name": {
            "en": "Wheat Rust (Yellow Rust / Stripped Rust)",
            "hi": "गेहूं का पीला रतवा (येलो रस्ट)"
        },
        "severity": {
            "en": "High",
            "hi": "उच्च"
        },
        "what_it_means": {
            "en": "A fungal disease caused by Puccinia striiformis that forms yellow stripes of pustules on leaves, disrupting photosynthesis and severely reducing grain yield.",
            "hi": "यह पक्सिनिया स्ट्रिफॉर्मिस कवक के कारण होने वाला रोग है, जो पत्तियों पर पीले रंग की धारियां बनाता है, जिससे प्रकाश संश्लेषण बाधित होता है और उपज में भारी कमी आती है।"
        },
        "immediate_actions": {
            "en": [
                "Isolate the infected field area to prevent spore dispersal.",
                "Avoid overhead irrigation as humidity facilitates spore growth.",
                "Notify local agricultural extension officers for community alert."
            ],
            "hi": [
                "संक्रमित क्षेत्र को अलग करें ताकि हवा से बीजाणु न फैलें।",
                "फव्वारा सिंचाई से बचें क्योंकि नमी से बीमारी बढ़ती है।",
                "समुदाय को सचेत करने के लिए स्थानीय कृषि अधिकारियों को सूचित करें।"
            ]
        },
        "recommended_treatment": {
            "en": "Apply Propiconazole 25% EC at 200 ml per acre mixed with 200 liters of water immediately upon detection.",
            "hi": "लक्षण दिखते ही प्रोपिकोनाज़ोल 25% ईसी (200 मिली प्रति एकड़) को 200 लीटर पानी में मिलाकर छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Sow rust-resistant wheat varieties recommended for your region.",
                "Practice early sowing to avoid peak humidity periods.",
                "Monitor nitrogen fertilizer use, as excess nitrogen promotes foliage growth vulnerable to rust."
            ],
            "hi": [
                "अपने क्षेत्र के लिए अनुशंसित रतवा-प्रतिरोधी गेहूं की किस्मों की बुआई करें।",
                "अधिक नमी वाले समय से बचने के लिए समय पर बुआई करें।",
                "नाइट्रोजन उर्वरक का संतुलित उपयोग करें, अधिक नाइट्रोजन रोग को बढ़ावा देता है।"
            ]
        },
        "risk_level": {
            "en": "High",
            "hi": "उच्च"
        }
    },
    "YELLOW_RUST": {
        "disease_name": {
            "en": "Yellow Rust",
            "hi": "पीला रतवा (येलो रस्ट)"
        },
        "severity": {
            "en": "High",
            "hi": "उच्च"
        },
        "what_it_means": {
            "en": "A fungal disease causing yellow stripe-like pustules on wheat leaves, hindering grain development.",
            "hi": "एक कवक जनित रोग जो गेहूं की पत्तियों पर पीली पट्टीदार धारियां बनाता है, जिससे दानों का विकास रुक जाता है।"
        },
        "immediate_actions": {
            "en": [
                "Stop sprinkler/overhead irrigation immediately.",
                "Spray systemic fungicide on the affected patch."
            ],
            "hi": [
                "फव्वारा सिंचाई तुरंत बंद करें।",
                "प्रभावित हिस्से पर प्रणालीगत कवकनाशी का छिड़काव करें।"
            ]
        },
        "recommended_treatment": {
            "en": "Spray Propiconazole 25% EC (Tebuconazole alternative) at 1 ml/liter of water.",
            "hi": "प्रोपिकोनाज़ोल 25% ईसी का 1 मिली प्रति लीटर पानी की दर से छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Use rust-resistant seeds.",
                "Avoid late sowing of wheat."
            ],
            "hi": [
                "रोग-प्रतिरोधी बीजों का प्रयोग करें।",
                "गेहूं की देर से बुआई न करें।"
            ]
        },
        "risk_level": {
            "en": "High",
            "hi": "उच्च"
        }
    },
    "POWDERY_MILDEW": {
        "disease_name": {
            "en": "Powdery Mildew",
            "hi": "चूर्णिल आसिता (पाउडर जैसी फफूंदी)"
        },
        "severity": {
            "en": "Medium",
            "hi": "मध्यम"
        },
        "what_it_means": {
            "en": "A fungal infection characterized by white, powdery patches on leaf surfaces and stems, leading to yellowing and premature leaf fall.",
            "hi": "यह कवक रोग है जिसमें पत्तियों और तनों पर सफेद पाउडर जैसे धब्बे बन जाते हैं, जिससे पत्तियां पीली होकर समय से पहले गिर जाती हैं।"
        },
        "immediate_actions": {
            "en": [
                "Prune and safely destroy infected leaves to reduce spore load.",
                "Ensure proper row spacing to maximize sunlight penetration and air flow."
            ],
            "hi": [
                "संक्रमित पत्तियों को काटकर सुरक्षित नष्ट करें ताकि रोग न फैले।",
                "हवा और धूप के प्रवेश के लिए पौधों के बीच उचित दूरी सुनिश्चित करें।"
            ]
        },
        "recommended_treatment": {
            "en": "Spray Wettable Sulfur 80% WP at 2 g per liter of water or apply Dinocap/Hexaconazole.",
            "hi": "घुलनशील सल्फर 80% डब्ल्यूपी (2 ग्राम प्रति लीटर पानी) या हेक्साकोनाज़ोल का छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Avoid planting in deeply shaded areas.",
                "Use balanced fertilizer schedules."
            ],
            "hi": [
                "गहरी छाया वाले स्थानों में बुआई से बचें।",
                "संतुलित खाद और उर्वरक का उपयोग करें।"
            ]
        },
        "risk_level": {
            "en": "Medium",
            "hi": "मध्यम"
        }
    },
    "BLAST": {
        "disease_name": {
            "en": "Rice Blast",
            "hi": "धान का झोंका रोग (ब्लास्ट)"
        },
        "severity": {
            "en": "High",
            "hi": "उच्च"
        },
        "what_it_means": {
            "en": "A highly damaging fungal disease affecting leaves, nodes, and panicles of rice, forming diamond-shaped lesions.",
            "hi": "धान का एक अत्यंत विनाशकारी कवक रोग जो पत्तियों, गांठों और बालियों को प्रभावित करता है, जिससे नाव के आकार के धब्बे बनते हैं।"
        },
        "immediate_actions": {
            "en": [
                "Drain the field temporarily to lower relative humidity around the canopy.",
                "Suspend nitrogen application, as high nitrogen exacerbates blast severity."
            ],
            "hi": [
                "नमी कम करने के लिए खेत से अतिरिक्त पानी निकालें।",
                "नाइट्रोजन का छिड़काव तुरंत रोकें, क्योंकि इससे रोग तेजी से फैलता है।"
            ]
        },
        "recommended_treatment": {
            "en": "Spray Tricyclazole 75% WP at 0.6 g per liter of water or Isoprothiolane 40% EC.",
            "hi": "ट्राइसाइक्लाजोल 75% डब्ल्यूपी (0.6 ग्राम प्रति लीटर पानी) या आइसोप्रोपियोलेन का छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Burn stubble of previous infected crops to eliminate overwintering spores.",
                "Treat seeds with Carbendazim before sowing."
            ],
            "hi": [
                "बीजाणुओं को नष्ट करने के लिए संक्रमित फसल के अवशेषों को जलाएं या नष्ट करें।",
                "बुआई से पहले बीजों का कार्बेन्डाजिम से उपचार करें।"
            ]
        },
        "risk_level": {
            "en": "High",
            "hi": "उच्च"
        }
    },
    "BROWN_SPOT": {
        "disease_name": {
            "en": "Brown Spot",
            "hi": "भूरा धब्बा रोग (ब्राउन स्पॉट)"
        },
        "severity": {
            "en": "Medium",
            "hi": "मध्यम"
        },
        "what_it_means": {
            "en": "Fungal infection causing oval, dark-brown spots with yellow halos on rice leaves, typically associated with nutrient-deficient soils.",
            "hi": "कवक जनित रोग जो धान की पत्तियों पर पीले घेरे वाले भूरे रंग के अंडाकार धब्बे बनाता है, यह अक्सर पोषक तत्वों की कमी वाली मिट्टी में होता है।"
        },
        "immediate_actions": {
            "en": [
                "Apply potassium-rich fertilizers as top dressing to help plants resist the disease.",
                "Ensure constant moderate moisture; avoid dry soil stress."
            ],
            "hi": [
                "प्रतिरोधक क्षमता बढ़ाने के लिए पोटेशियम युक्त खादों का छिड़काव करें।",
                "मिट्टी में पर्याप्त नमी बनाए रखें, सूखापन न आने दें।"
            ]
        },
        "recommended_treatment": {
            "en": "Spray Mancozeb 75% WP at 2 g per liter of water or Propiconazole.",
            "hi": "मैंकोजेब 75% डब्ल्यूपी (2 ग्राम प्रति लीटर पानी) या प्रोपिकोनाज़ोल का छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Test soil and address deficiency of nitrogen, potassium, and silicon.",
                "Perform seed hot-water treatment before nursery sowing."
            ],
            "hi": [
                "मिट्टी की जांच करवाएं और नाइट्रोजन, पोटेशियम व सिलिकॉन की कमी को दूर करें।",
                "नर्सरी में बुआई से पहले गर्म पानी से बीजोपचार करें।"
            ]
        },
        "risk_level": {
            "en": "Medium",
            "hi": "मध्यम"
        }
    },
    "LATE_BLIGHT": {
        "disease_name": {
            "en": "Late Blight",
            "hi": "पछैती झुलसा (लेट ब्लाइट)"
        },
        "severity": {
            "en": "High",
            "hi": "उच्च"
        },
        "what_it_means": {
            "en": "A catastrophic oomycete disease of potato/tomato causing rapid rotting of leaves, stems, and tubers under cool, wet conditions.",
            "hi": "आलू और टमाटर का अत्यंत विनाशकारी रोग जो ठंडे और गीले मौसम में पत्तियों, तनों और कंदों को तेजी से सड़ाता है।"
        },
        "immediate_actions": {
            "en": [
                "Check daily weather forecasts; cold, humid weather triggers rapid spread.",
                "Immediately destroy affected plants showing water-soaked lesions."
            ],
            "hi": [
                "मौसम के पूर्वानुमान पर नजर रखें; ठंडा और नम मौसम रोग को बढ़ाता है।",
                "पानी से भीगे हुए धब्बे दिखाने वाले ग्रसित पौधों को तुरंत नष्ट करें।"
            ]
        },
        "recommended_treatment": {
            "en": "Spray Metalaxyl 8% + Mancozeb 64% WP (Krilaxyl) at 2.5 g per liter of water.",
            "hi": "मेटालैक्सिल 8% + मैंकोजेब 64% डब्ल्यूपी (2.5 ग्राम प्रति लीटर पानी) का छिड़काव करें।"
        },
        "prevention_advice": {
            "en": [
                "Plant certified disease-free seed tubers.",
                "Ensure proper crop rotation patterns (avoid solanaceous sequences)."
            ],
            "hi": [
                "प्रमाणित रोगमुक्त आलू कंदों की ही बुआई करें।",
                "उचित फसल चक्र अपनाएं (एक ही परिवार की फसलें लगातार न लगाएं)।"
            ]
        },
        "risk_level": {
            "en": "High",
            "hi": "उच्च"
        }
    },
    "EARLY_BLIGHT": {
        "disease_name": {
            "en": "Early Blight",
            "hi": "अगेती झुलसा (अर्ली ब्लाइट)"
        },
        "severity": {
            "en": "Medium",
            "hi": "मध्यम"
        },
        "what_it_means": {
            "en": "Fungal infection causing dark, concentric target-board spots on older leaves, reducing photosynthetic efficiency.",
            "hi": "कवक जनित रोग जो निचली पत्तियों पर चक्राकार काले धब्बे बनाता है, जिससे प्रकाश संश्लेषण क्षमता कम हो जाती है।"
        },
        "immediate_actions": {
            "en": [
                "Remove and burn lower yellowing leaves that touch the soil.",
                "Mulch to prevent soil-borne spores from splashing onto leaves."
            ],
            "hi": [
                "मिट्टी को छूने वाली पीली निचली पत्तियों को हटाकर नष्ट कर दें।",
                "मिट्टी से बीजाणुओं को पत्तियों पर उछलने से रोकने के लिए मल्चिंग करें।"
            ]
        },
        "recommended_treatment": {
            "en": "Apply Chlorothalonil 75% WP at 2 g/liter or Copper Oxychloride 50% WP.",
            "hi": "क्लोरोथैलोनिल 75% डब्ल्यूपी (2 ग्राम प्रति लीटर) या कॉपर ऑक्सीक्लोराइड का प्रयोग करें।"
        },
        "prevention_advice": {
            "en": [
                "Maintain vigorous crop health with balanced NPK fertilizer application.",
                "Practice clean cultivation and weed management."
            ],
            "hi": [
                "संतुलित एनपीके उर्वरकों द्वारा फसल को स्वस्थ और मजबूत रखें।",
                "खेत की सफाई और खरपतवार नियंत्रण पर ध्यान दें।"
            ]
        },
        "risk_level": {
            "en": "Medium",
            "hi": "मध्यम"
        }
    },
    "RED_ROT": {
        "disease_name": {
            "en": "Red Rot of Sugarcane",
            "hi": "गन्ने का लाल सड़न रोग (रेड रॉट)"
        },
        "severity": {
            "en": "High",
            "hi": "उच्च"
        },
        "what_it_means": {
            "en": "A lethal fungal disease in sugarcane causing internal stalk reddening with white patches, sour odor, and leaf drying.",
            "hi": "गन्ने का एक घातक रोग जिससे तने के अंदर सफ़ेद धब्बों के साथ लालिमा आ जाती है, सिरके जैसी गंध आती है और पत्तियाँ सूख जाती हैं।"
        },
        "immediate_actions": {
            "en": [
                "Uproot and burn the entire clump of the infected cane.",
                "Isolate the channel to avoid water flowing from infected clumps to healthy crops."
            ],
            "hi": [
                "संक्रमित गन्ने के पूरे थान (झुंड) को उखाड़कर तुरंत जला दें।",
                "सिंचाई नाली को अलग करें ताकि संक्रमित पानी स्वस्थ गन्नों तक न जाए।"
            ]
        },
        "recommended_treatment": {
            "en": "No effective chemical cure exists once inside the stalk. Uproot immediately. Soil drenching with Carbendazim 50% WP can limit spread.",
            "hi": "तने के अंदर संक्रमण होने पर कोई रासायनिक इलाज नहीं है। संक्रमित पौधे उखाड़ें। फैलाव रोकने के लिए कार्बेन्डाजिम से मिट्टी का उपचार करें।"
        },
        "prevention_advice": {
            "en": [
                "Use healthy seed setts from disease-free nurseries.",
                "Adopt 2-3 years crop rotation with paddy or green manures."
            ],
            "hi": [
                "रोगमुक्त नर्सरी से स्वस्थ बीज गन्नों (setts) का ही चयन करें।",
                "धान या हरी खाद के साथ 2-3 वर्षों का फसल चक्र अपनाएं।"
            ]
        },
        "risk_level": {
            "en": "High",
            "hi": "उच्च"
        }
    },
    "UNKNOWN": {
        "disease_name": {
            "en": "Unknown Anomaly",
            "hi": "अज्ञात असामान्यता"
        },
        "severity": {
            "en": "None",
            "hi": "कोई नहीं"
        },
        "what_it_means": {
            "en": "Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf.",
            "hi": "बीमारी की विश्वासपूर्वक पहचान करने में असमर्थ। कृपया प्रभावित पत्ती की एक स्पष्ट क्लोज़-अप तस्वीर अपलोड करें।"
        },
        "immediate_actions": {
            "en": [
                "Take another clear photo in good lighting.",
                "Compare symptoms with healthy plants nearby."
            ],
            "hi": [
                "अच्छी रोशनी में एक और स्पष्ट तस्वीर लें।",
                "आसपास के स्वस्थ पौधों से लक्षणों की तुलना करें।"
            ]
        },
        "recommended_treatment": {
            "en": None,
            "hi": None
        },
        "prevention_advice": {
            "en": [
                "Maintain crop health through balanced watering and NPK inputs."
            ],
            "hi": [
                "संतुलित सिंचाई और एनपीके इनपुट के माध्यम से फसल का स्वास्थ्य बनाए रखें।"
            ]
        },
        "risk_level": {
            "en": "Low",
            "hi": "निम्न"
        }
    },
    "HEALTHY": {
        "disease_name": {
            "en": "Healthy Crop",
            "hi": "स्वस्थ फसल"
        },
        "severity": {
            "en": "None",
            "hi": "कोई नहीं"
        },
        "what_it_means": {
            "en": "Your crop foliage appears healthy with no visible symptoms of disease.",
            "hi": "आपकी फसल की पत्तियां स्वस्थ दिख रही हैं और बीमारी का कोई लक्षण नहीं है।"
        },
        "immediate_actions": {
            "en": [
                "No immediate treatment needed.",
                "Continue regular watering and nutrient schedules."
            ],
            "hi": [
                "किसी तत्काल उपचार की आवश्यकता नहीं है।",
                "नियमित सिंचाई और पोषण जारी रखें।"
            ]
        },
        "recommended_treatment": {
            "en": None,
            "hi": None
        },
        "prevention_advice": {
            "en": [
                "Monitor crops weekly for any pest or disease onset.",
                "Practice clean crop maintenance."
            ],
            "hi": [
                "कीट या रोग के किसी भी लक्षण के लिए साप्ताहिक रूप से फसलों की निगरानी करें।",
                "स्वच्छ कृषि पद्धतियां अपनाएं।"
            ]
        },
        "risk_level": {
            "en": "Low",
            "hi": "निम्न"
        }
    }
}

DEFAULT_GUIDANCE = DISEASE_GUIDANCE["UNKNOWN"]


def get_disease_guidance(disease_tag: str, lang: str = "en") -> Dict[str, Any]:
    norm_tag = disease_tag.strip().upper().replace("-", "_").replace(" ", "_")
    guidance = DISEASE_GUIDANCE.get(norm_tag, DEFAULT_GUIDANCE)
    
    # Return translated fields directly
    target_lang = "hi" if lang == "hi" else "en"
    
    # Handle optional/None fields gracefully
    return {
        "disease_name": guidance["disease_name"].get(target_lang, guidance["disease_name"]["en"]) if guidance["disease_name"] else None,
        "severity": guidance["severity"].get(target_lang, guidance["severity"]["en"]) if guidance["severity"] else None,
        "what_it_means": guidance["what_it_means"].get(target_lang, guidance["what_it_means"]["en"]) if guidance["what_it_means"] else None,
        "immediate_actions": guidance["immediate_actions"].get(target_lang, guidance["immediate_actions"]["en"]) if guidance["immediate_actions"] else None,
        "recommended_treatment": guidance["recommended_treatment"].get(target_lang, guidance["recommended_treatment"]["en"]) if guidance.get("recommended_treatment") else None,
        "prevention_advice": guidance["prevention_advice"].get(target_lang, guidance["prevention_advice"]["en"]) if guidance["prevention_advice"] else None,
        "risk_level": guidance["risk_level"].get(target_lang, guidance["risk_level"]["en"]) if guidance["risk_level"] else None,
    }
