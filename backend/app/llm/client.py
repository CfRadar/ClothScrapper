import asyncio
import json
import logging
import random
from typing import Literal, TypeVar, Union

import httpx
from backend.app import quota
from backend.app.config import Settings, get_settings
from backend.app.llm.json_utils import JSONExtractError, parse_model
from backend.app.llm.limiter import TokenBucketLimiter
from pydantic import BaseModel

logger = logging.getLogger("backend.llm")

T = TypeVar("T", bound=BaseModel)


class QuotaExceeded(Exception):
    """Raised when the daily free-tier LLM call quota is exhausted."""

    pass


class LLMCallError(Exception):
    """Raised when an LLM call fails across all fallback models."""

    pass


class OpenRouterClient:
    def __init__(
        self,
        settings: Settings | None = None,
        limiter: TokenBucketLimiter | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.limiter = limiter or TokenBucketLimiter(rpm_limit=self.settings.LLM_RPM_LIMIT)
        self._http_client = http_client
        self.llm_calls_used: int = 0

    def get_models_for_role(self, role: Literal["planner", "analyst", "social"]) -> list[str]:
        """Resolve ordered, deduplicated model list for the given agent role."""
        primary_map = {
            "planner": self.settings.MODEL_PLANNER,
            "analyst": self.settings.MODEL_ANALYST,
            "social": self.settings.MODEL_SOCIAL,
        }
        role_primary = primary_map.get(role, "")
        chain = []
        if role_primary:
            chain.append(role_primary)
        chain.extend(self.settings.parsed_model_fallbacks)

        # Deduplicate preserving order
        deduped = []
        for m in chain:
            if m and m not in deduped:
                deduped.append(m)

        if not deduped:
            # Fallback default if no models configured yet
            deduped = ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free"]
        return deduped

    async def _dispatch_http(
        self,
        client: httpx.AsyncClient,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Execute a single HTTP call to OpenRouter with quota and limiter checks."""
        # 1. Quota check
        if not await quota.can_call(
            db_path=self.settings.DATABASE_PATH,
            daily_limit=self.settings.LLM_DAILY_LIMIT,
        ):
            raise QuotaExceeded("Daily OpenRouter free tier limit has been reached.")

        # 2. Rate limiter wait
        await self.limiter.acquire()

        # 3. Headers (Never log key)
        api_key = self.settings.OPENROUTER_API_KEY.get_secret_value()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": self.settings.APP_REFERER,
            "X-Title": self.settings.APP_TITLE,
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        url = f"{self.settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
        logger.info(
            f"Dispatching LLM call to model='{model}', prompt_len={len(system_prompt) + len(user_prompt)}"
        )

        # Increment call trackers
        self.llm_calls_used += 1
        await quota.record(model, db_path=self.settings.DATABASE_PATH)

        response = await client.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.settings.LLM_TIMEOUT_SECONDS,
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait_s = float(retry_after) if retry_after and retry_after.isdigit() else 2.0
            raise httpx.HTTPStatusError(
                f"Rate limited (429). Retry-After: {wait_s}s",
                request=response.request,
                response=response,
            )

        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content")
        if not content:
            content = msg.get("reasoning", "")
        return content or ""

    async def chat(
        self,
        *,
        role: Literal["planner", "analyst", "social"],
        system: str,
        user: str,
        schema: type[T] | None = None,
        max_tokens: int = 2500,
        temperature: float = 0.3,
    ) -> Union[T, str]:
        """
        Execute chat completion with fallback model chain, 429 backoff,
        and defensive JSON repair.
        """
        models = self.get_models_for_role(role)
        final_system = system

        if schema is not None:
            schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"))
            final_system = (
                f"{system}\n\n"
                f"IMPORTANT: Respond with a single valid JSON object and nothing else. "
                f"No markdown formatting, no code fences, no commentary.\n"
                f"JSON Schema:\n{schema_json}"
            )

        client_ctx = self._http_client
        owns_client = False
        if client_ctx is None:
            client_ctx = httpx.AsyncClient()
            owns_client = True

        total_attempts = 0
        max_attempts = 4
        last_error = None

        try:
            for model_idx, model in enumerate(models):
                if total_attempts >= max_attempts:
                    break

                backoff_delays = [2.0, 4.0, 8.0]
                backoff_idx = 0

                while total_attempts < max_attempts:
                    total_attempts += 1
                    try:
                        raw_content = await self._dispatch_http(
                            client_ctx,
                            model=model,
                            system_prompt=final_system,
                            user_prompt=user,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )

                        if schema is None:
                            return raw_content

                        # Parse schema
                        try:
                            return parse_model(raw_content, schema)
                        except JSONExtractError as parse_err:
                            logger.warning(
                                f"Model {model} output failed schema parsing: {parse_err}. Attempting 1-shot repair."
                            )
                            # 1 repair retry on same model
                            repair_prompt = (
                                f"The following response is invalid JSON or does not match the schema.\n"
                                f"Response:\n{raw_content}\n\n"
                                f"Return only the corrected valid JSON object and nothing else."
                            )
                            total_attempts += 1
                            repaired_content = await self._dispatch_http(
                                client_ctx,
                                model=model,
                                system_prompt=final_system,
                                user_prompt=repair_prompt,
                                temperature=0.1,
                                max_tokens=max_tokens,
                            )
                            return parse_model(repaired_content, schema)

                    except QuotaExceeded:
                        raise
                    except (
                        httpx.HTTPStatusError,
                        httpx.TimeoutException,
                        httpx.RequestError,
                    ) as net_err:
                        last_error = net_err
                        if isinstance(net_err, httpx.HTTPStatusError):
                            if net_err.response.status_code in (401, 403):
                                logger.error(
                                    f"Authentication error {net_err.response.status_code}. Not attempting fallbacks with invalid key."
                                )
                                raise LLMCallError(
                                    f"OpenRouter authentication failed ({net_err.response.status_code}). Please verify OPENROUTER_API_KEY."
                                )

                        is_429 = (
                            isinstance(net_err, httpx.HTTPStatusError)
                            and net_err.response.status_code == 429
                        )
                        logger.warning(
                            f"Error calling {model} (attempt {total_attempts}): {net_err}"
                        )

                        if is_429:
                            delay = backoff_delays[
                                min(backoff_idx, len(backoff_delays) - 1)
                            ] + random.uniform(0.1, 0.8)
                            backoff_idx += 1
                            await asyncio.sleep(delay)
                            # Switch to next fallback model on 429
                            break
                        else:
                            # 5xx or timeout: switch to next fallback model
                            break
                    except JSONExtractError as final_json_err:
                        last_error = final_json_err
                        logger.warning(f"Model {model} repair failed. Switching to next model.")
                        break

            raise LLMCallError(
                f"All LLM attempts ({total_attempts}) failed. Last error: {last_error}"
            )

        finally:
            if owns_client:
                await client_ctx.aclose()
