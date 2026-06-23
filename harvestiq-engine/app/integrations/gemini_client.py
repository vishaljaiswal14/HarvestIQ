import base64
import json
from typing import Optional

import httpx

from app.core.config import get_settings


class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        text_model: Optional[str] = None,
    ):
        settings = get_settings()

        print("OPENROUTER FROM SETTINGS =", repr(getattr(settings, "openrouter_api_key", None)))
        print("GEMINI FROM SETTINGS =", repr(settings.gemini_api_key))
        
        self.openrouter_api_key = (
            api_key
            or getattr(settings, "openrouter_api_key", "")
        )
        self.gemini_api_key = settings.gemini_api_key

        # Maintain backward compatibility with self.api_key
        self.api_key = self.openrouter_api_key or self.gemini_api_key

        print(
            "OPENROUTER API KEY PREFIX =",
            self.openrouter_api_key[:15] if self.openrouter_api_key else "EMPTY"
        )
        print(
            "GEMINI API KEY PREFIX =",
            self.gemini_api_key[:15] if self.gemini_api_key else "EMPTY"
        )

        self.model = model or "google/gemini-2.0-flash"
        self.text_model = text_model or "google/gemma-4-26b-a4b-it:free"

        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"

        print(
            f"[OpenRouterClient] Loaded. Vision={self.model} Text={self.text_model}"
        )

    async def _call_vision_api(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
    ) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")

        if self.openrouter_api_key:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://harvestiq.app",
                "X-Title": "HarvestIQ",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}"
                                },
                            },
                        ],
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.openrouter_url,
                    headers=headers,
                    json=payload,
                    timeout=60.0,
                )

            print("OPENROUTER STATUS =", response.status_code)
            if response.status_code != 200:
                print("OPENROUTER ERROR BODY =", response.text)
            response.raise_for_status()
            data = response.json()
            resp_content = data["choices"][0]["message"]["content"]
            print("RAW VISION RESPONSE (OpenRouter) =", repr(resp_content), flush=True)
            return resp_content
        else:
            settings = get_settings()
            groq_key = settings.groq_api_key
            if not groq_key:
                raise ValueError("Neither OPENROUTER_API_KEY nor GROQ_API_KEY is configured.")

            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}"
                                },
                            },
                        ],
                    }
                ],
                "response_format": {"type": "json_object"},
            }

            url = "https://api.groq.com/openai/v1/chat/completions"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=60.0,
                )

            print("GROQ VISION STATUS =", response.status_code)
            if response.status_code != 200:
                print("GROQ VISION ERROR BODY =", response.text)
            response.raise_for_status()
            data = response.json()
            resp_content = data["choices"][0]["message"]["content"]
            print("RAW VISION RESPONSE (Groq) =", repr(resp_content), flush=True)
            return resp_content

    async def identify_crop(
        self,
        image_bytes: bytes,
        mime_type: str,
        registered_crop: Optional[str] = None,
    ) -> dict:
        prompt = (
            "You are an image classifier for an agricultural platform. Analyze the uploaded image and identify what crop is primarily visible.\n"
            "Typical crop categories are: WHEAT, RICE, POTATO, TOMATO, SUGARCANE.\n"
        )
        if registered_crop:
            prompt += (
                f"The expected registered crop for this farm is: {registered_crop}.\n"
                f"Your primary task is to identify if the crop visible in the image is {registered_crop}. "
                f"If the visual features (such as leaf shape, texture, color, venation, and pattern) are consistent with {registered_crop}, return '{registered_crop}'. "
                f"If it is clearly a different crop from the typical categories, return that crop name (e.g., if it is clearly tomato, return 'TOMATO'). "
                f"If no crop can be identified at all (e.g. not a plant, or extremely blurry), return 'UNKNOWN'.\n"
            )
        else:
            prompt += "Identify the crop. If no crop can be identified, return 'UNKNOWN'.\n"

        prompt += (
            "Provide your true confidence estimation as a float between 0.0 and 1.0.\n\n"
            "Return ONLY a valid JSON object matching this structure:\n"
            "{\n"
        )
        example_crop = registered_crop or "WHEAT"
        prompt += f'  "crop_type": "{example_crop}",\n'
        prompt += (
            '  "crop_confidence": 0.85\n'
            "}\n\n"
            "Requirements:\n"
            "1. Output ONLY JSON, do not wrap in markdown or add explanations.\n"
            "2. Estimate your confidence based on visual features. Do not hardcode values."
        )

        content = await self._call_vision_api(prompt, image_bytes, mime_type)
        try:
            parsed = json.loads(content.strip().replace("```json", "").replace("```", ""))
            crop_type = str(parsed.get("crop_type", "UNKNOWN")).strip().upper()
            crop_conf = float(parsed.get("crop_confidence", 0.0))
        except Exception:
            crop_type = "UNKNOWN"
            crop_conf = 0.0

        return {
            "crop_type": crop_type,
            "crop_confidence": crop_conf,
        }

    async def validate_image(
        self,
        image_bytes: bytes,
        mime_type: str,
    ) -> dict:
        prompt = (
            "You are an image classifier for an agricultural platform. Analyze the content of the uploaded image.\n"
            "You MUST classify the image into one of the following classes: "
            "CROP_LEAF, CROP_CANOPY, AGRICULTURAL_FIELD, HUMAN, ANIMAL, VEHICLE, BUILDING, DOCUMENT, SCREENSHOT, BLANK_IMAGE, UNKNOWN.\n\n"
            "Return ONLY a valid JSON object matching this structure:\n"
            "{\n"
            '  "valid": true or false,\n'
            '  "image_type": "CROP_LEAF" (or the classified class),\n'
            '  "validation_confidence": 0.95 (float confidence of class prediction),\n'
            '  "reason": "NOT_CROP_IMAGE" (include this only when valid is false),\n'
            '  "message": "Please upload a crop leaf, crop canopy, or agricultural field image." (only when valid is false)\n'
            "}\n\n"
            "Requirements:\n"
            "1. An image is valid (valid=true) ONLY if its type is CROP_LEAF, CROP_CANOPY, or AGRICULTURAL_FIELD.\n"
            "2. If valid=false, set reason to 'NOT_CROP_IMAGE' and message to exactly 'Please upload a crop leaf, crop canopy, or agricultural field image.'\n"
            "3. If the image is a selfie, a face, or contains any human body part, the type MUST be HUMAN.\n"
            "4. If the image is blank or nearly single-colored, the type MUST be BLANK_IMAGE.\n"
            "5. If it is a screenshot, the type MUST be SCREENSHOT.\n"
            "6. Output ONLY JSON, do not wrap in markdown or add explanations."
        )

        content = await self._call_vision_api(prompt, image_bytes, mime_type)
        parsed = json.loads(content.strip().replace("```json", "").replace("```", ""))
        
        img_type = str(parsed.get("image_type", "UNKNOWN")).upper()
        is_valid = img_type in {"CROP_LEAF", "CROP_CANOPY", "AGRICULTURAL_FIELD"}
        val_conf = float(parsed.get("validation_confidence", 0.0))
        
        res = {
            "valid": is_valid,
            "image_type": img_type,
            "validation_confidence": val_conf,
        }
        if not is_valid:
            res["reason"] = "NOT_CROP_IMAGE"
            res["message"] = parsed.get("message") or "Please upload a crop leaf, crop canopy, or agricultural field image."
        return res

    async def detect_disease(
        self,
        image_bytes: bytes,
        mime_type: str,
        crop_type: str,
        state: str,
        allowed_diseases: Optional[list[str]] = None,
    ) -> dict:
        allowed_diseases = allowed_diseases or []
        allowed_list_str = "\n".join(f"- {d}" for d in allowed_diseases)
        prompt = (
            f"You are an agricultural crop disease detection system.\n"
            f"Crop: {crop_type}\n"
            f"State: {state}\n\n"
            "Analyze the crop image and identify if there is any disease.\n"
            "Choose ONLY one disease_tag from the following allowed diseases list:\n"
            f"{allowed_list_str}\n"
            "or\n"
            "- HEALTHY\n"
            "- UNKNOWN\n\n"
            "Return UNKNOWN if the disease is not in the allowed list.\n"
            "Estimate your confidence as a value between 0.0 and 1.0 based on the clarity of symptoms.\n\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "disease_tag": "CHOSEN_DISEASE_TAG",\n'
            '  "confidence": 0.85\n'
            "}\n"
            "Output ONLY valid JSON, do not add introductory text or markdown tags."
        )

        content = await self._call_vision_api(prompt, image_bytes, mime_type)
        parsed = json.loads(content.strip().replace("```json", "").replace("```", ""))

        conf_val = parsed.get("confidence")
        try:
            conf = float(conf_val) if conf_val is not None else None
        except (ValueError, TypeError):
            conf = None

        return {
            "disease": parsed.get("disease_tag", "UNKNOWN"),
            "confidence": conf,
            "raw_response": content,
        }

    async def synthesize_advisory(
        self,
        context_package: str,
        language: str,
        mitigation_locked: bool = False,
        briefing_mode: bool = False,
    ) -> str:
        settings = get_settings()
        
        if briefing_mode:
            if language.lower() == "hi":
                system_text = (
                    "आप एक कृषि सलाहकार सहायक हैं। फ़ार्म डेटा और वर्तमान परिस्थितियों के आधार पर एक संक्षिप्त और सूचनात्मक सुबह की कृषि ब्रीफिंग (Morning Briefing) तैयार करें।\n"
                    "इसे संक्षिप्त, क्रियात्मक और किसान के अनुकूल रखें।"
                )
            else:
                system_text = (
                    "You are an agricultural advisory assistant. Generate a concise and informative morning agricultural briefing summary based on the provided farm data and conditions.\n"
                    "Keep it brief, actionable, and farmer-friendly."
                )
        else:
            if language.lower() == "hi":
                system_text = (
                    "आप एक कृषि सलाहकार सहायक हैं। आपको किसान के प्रश्न का उत्तर देना होगा।\n"
                    "आपको अपने उत्तर को बिल्कुल इसी संरचित प्रारूप (structured layout) में प्रस्तुत करना होगा, और केवल इन चार अनुभागों को ही रखना होगा (QUESTION, ANSWER, या Source अनुभाग शामिल न करें), और उत्तर को अधिकतम 150-200 शब्दों में रखें:\n\n"
                    "Recommended Actions:\n"
                    "[किसान के लिए विशिष्ट और व्यावहारिक कदम यहाँ लिखें, यदि अधिक हैं तो नंबर 1., 2. दें]\n\n"
                    "Why This Matters:\n"
                    "[व्यावहारिक और किसान-अनुकूल शब्दों में कारण समझाएं। कभी भी आंतरिक तकनीकी टेलीमेट्री जैसे कि FSI मान, स्वास्थ्य स्कोर (health scores), आसपास के रोग आंकड़े, या आंतरिक विवरण शामिल न करें जब तक कि उपयोगकर्ता विशेष रूप से न पूछे। सरल विवरणों का उपयोग करें, जैसे 'मिट्टी में नमी की कमी है']\n\n"
                    "Expected Benefit:\n"
                    "[फसल या उपज पर होने वाले प्रत्यक्ष सकारात्मक परिणाम का वर्णन करें]\n\n"
                    "Priority:\n"
                    "[HIGH, MEDIUM, या LOW दर्ज करें]\n\n"
                    "नोट: सामान्य प्रश्नों (जैसे 'खेती में लाभ कैसे कमाएं?', 'सिंचाई कैसे करें?', या 'उपज में सुधार कैसे करें?') के लिए, किसी भी प्रणाली टेलीमेट्री को शामिल किए बिना किसान की फसल और क्षेत्र के लिए व्यावहारिक और क्रियाशील सलाह दें।"
                )
            else:
                system_text = (
                    "You are a helpful and expert agricultural advisor. You must answer the user's question.\n"
                    "You MUST format your response EXACTLY in the following structured layout, keeping ONLY these four sections (do not include QUESTION, ANSWER, or Source fields), and keep the response under 150-200 words:\n\n"
                    "Recommended Actions:\n"
                    "[Provide one or more specific, practical, and farmer-focused actionable recommendations, numbered if multiple]\n\n"
                    "Why This Matters:\n"
                    "[Explain the reason in simple, farmer-friendly terms. NEVER include internal technical telemetry such as FSI values, raw health scores, nearby disease radar statistics, or complex internal metrics unless the user explicitly asks for them. Use natural descriptions instead, e.g., 'Soil moisture is low' instead of 'FSI is 0.42']\n\n"
                    "Expected Benefit:\n"
                    "[Describe the direct positive impact on the crop or farm yield in farmer-friendly terms]\n\n"
                    "Priority:\n"
                    "[Specify HIGH, MEDIUM, or LOW based on urgency]\n\n"
                    "Note: For generic questions (such as 'How to make profit in farming?', 'How to irrigate?', or 'How to improve yield?'), generate highly actionable, practical advice suited to the farmer's crop and region, without leaking any system metrics or telemetry."
                )

        if mitigation_locked:
            system_text += "\n\nMitigation is locked. Do not invent treatments or recommend chemical pesticides/fungicides that are not already present in the knowledge base excerpts."

        # Check if we should route to OpenRouter or Google Gemini API
        is_openrouter = bool(self.openrouter_api_key and ("/" in self.text_model))

        if is_openrouter:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://harvestiq.app",
                "X-Title": "HarvestIQ",
            }
            # Map Gemini model names instead of OpenRouter specific free tags
            model_name = self.text_model
            if "gemma" in model_name or "free" in model_name:
                model_name = "google/gemini-2.0-flash"

            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_text
                    },
                    {
                        "role": "user",
                        "content": context_package
                    }
                ]
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.openrouter_url,
                        headers=headers,
                        json=payload,
                        timeout=60.0,
                    )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[OpenRouterClient] OpenRouter synthesis failed: {e}. Checking Groq fallback...", flush=True)
                groq_key = settings.groq_api_key
                if groq_key:
                    print("[OpenRouterClient] routing synthesis to Groq Llama 3.3...", flush=True)
                    return await self._call_groq_synthesis(context_package, system_text, groq_key)
                raise
        else:
            api_key = self.gemini_api_key or self.api_key
            if not api_key:
                groq_key = settings.groq_api_key
                if groq_key:
                    print("[OpenRouterClient] No Gemini key. routing synthesis to Groq Llama 3.3...", flush=True)
                    return await self._call_groq_synthesis(context_package, system_text, groq_key)
                raise ValueError("No API key configured for Gemini synthesis.")

            # Map model name for direct Gemini endpoint
            model_name = self.text_model or settings.gemini_text_model or "gemini-2.0-flash"
            if "/" in model_name:
                model_name = model_name.split("/")[-1]

            payload = {
                "systemInstruction": {
                    "parts": [
                        {
                            "text": system_text
                        }
                    ]
                },
                "contents": [
                    {
                        "parts": [
                            {
                                "text": context_package
                            }
                        ]
                    }
                ]
            }

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=60.0,
                    )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"[OpenRouterClient] Gemini direct synthesis failed: {e}. Checking Groq fallback...", flush=True)
                groq_key = settings.groq_api_key
                if groq_key:
                    print("[OpenRouterClient] routing synthesis to Groq Llama 3.3...", flush=True)
                    return await self._call_groq_synthesis(context_package, system_text, groq_key)
                raise

    async def _call_groq_synthesis(self, context_package: str, system_instruction: str, api_key: str) -> str:
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": context_package}
            ]
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                groq_url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language: Optional[str] = None,
    ) -> dict:
        import base64
        encoded = base64.b64encode(audio_bytes).decode("utf-8")

        prompt = "Transcribe this audio. Return ONLY the transcribed text. Do not add any introduction or explanation."
        if language and language != "auto":
            prompt += f" The audio is in {language} language, transcribe it accordingly."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": encoded,
                            }
                        },
                    ]
                }
            ]
        }

        model = self.text_model
        if "/" in model or not model:
            model = "gemini-2.0-flash"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0,
            )

        response.raise_for_status()
        data = response.json()

        try:
            transcript = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response structure from Gemini API: {e}")

        return {
            "transcript": transcript,
            "confidence": 1.0,
        }