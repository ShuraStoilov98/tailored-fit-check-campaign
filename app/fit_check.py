import base64
import json
import logging

import openai
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.prompts import SYSTEM_PROMPT, build_user_message
from app.schemas import FitCheckModelOutput, FitCheckResponse

logger = logging.getLogger(__name__)

_client: openai.AsyncOpenAI | None = None

_MOCK_RESPONSE = FitCheckResponse(
    verdict_label="Strong base",
    one_line_verdict="Clean foundation with one easy tweak.",
    overall_score=4,
    fit_score=4,
    style_score=3,
    colour_score=4,
    what_works=["Balanced base", "Palette feels cohesive"],
    improvements=[
        "Add one sharper finishing touch",
        "Choose cleaner shoe lines",
        "Use one subtle accessory",
    ],
    occasion_fit="Works well for the occasion.",
    tailored_tip="Small styling changes can make the outfit feel more intentional.",
)


def _get_client(api_key: str) -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=api_key, timeout=30.0)
    return _client


async def generate_fit_check(
    *,
    image_bytes: bytes,
    content_type: str,
    occasion: str | None,
) -> FitCheckModelOutput:
    settings = get_settings()

    if not settings.openai_api_key:
        if settings.environment == "local":
            logger.info("OPENAI_API_KEY not set; returning mock Fit Check.")
            return FitCheckModelOutput(
                outfit_detected=True,
                fit_check=_MOCK_RESPONSE,
            )
        raise HTTPException(status_code=500, detail="Service configuration error.")

    b64 = base64.standard_b64encode(image_bytes).decode()
    data_url = f"data:{content_type};base64,{b64}"
    client = _get_client(settings.openai_api_key)

    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.4,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "low"},
                        },
                        {"type": "text", "text": build_user_message(occasion)},
                    ],
                },
            ],
        )
    except (openai.APIConnectionError, openai.APIStatusError, openai.OpenAIError) as exc:
        logger.warning("OpenAI error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="We couldn't complete your Fit Check right now. Please try again in a moment.",
        )

    raw = completion.choices[0].message.content or ""

    try:
        data = json.loads(raw)
        fit_check = data.get("fit_check")
        if isinstance(fit_check, dict):
            for field in ("overall_score", "fit_score", "style_score", "colour_score"):
                if isinstance(fit_check.get(field), (int, float)):
                    fit_check[field] = max(1, min(5, int(fit_check[field])))
        return FitCheckModelOutput(**data)
    except (json.JSONDecodeError, ValidationError, TypeError, KeyError) as exc:
        logger.warning("Response parse error: %s | raw: %.200s", exc, raw)
        raise HTTPException(
            status_code=502,
            detail="We couldn't complete your Fit Check right now. Please try again in a moment.",
        )
