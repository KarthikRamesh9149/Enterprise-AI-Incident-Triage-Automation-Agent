from app.core.config import get_settings


class LLMProvider:
    def synthesize_incident_summary(self, context: str) -> str:
        settings = get_settings()
        if settings.llm_provider.lower() != "openai":
            return self._mock_summary(context)
        if not settings.openai_api_key:
            return (
                self._mock_summary(context)
                + " OpenAI provider was requested but no API key is configured."
            )
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.responses.create(
                model=settings.openai_chat_model,
                instructions=(
                    "You are an enterprise incident response assistant. "
                    "Summarize only the provided local incident evidence. "
                    "Do not infer customer impact, request volume, success rates, regions, "
                    "owners, or metrics unless explicitly present in the evidence packet. "
                    "Do not invent external actions, secrets, or production claims. "
                    "Any mitigation or communication action must be described as pending "
                    "human approval when the evidence says approval is required. "
                    "Return concise Markdown with these sections: Assessment, Evidence, "
                    "Recommended Next Step, Safety Gate."
                ),
                input=(
                    "Create an executive-quality incident triage summary for an internal "
                    "SRE incident commander. Keep it under 180 words. If evidence is absent, "
                    "say so instead of filling the gap.\n\n"
                    f"{context}"
                ),
                max_output_tokens=settings.max_output_tokens,
                temperature=settings.llm_temperature,
            )
            return response.output_text
        except Exception as exc:
            return (
                f"{self._mock_summary(context)} OpenAI synthesis failed locally: "
                f"{type(exc).__name__}."
            )

    @staticmethod
    def _mock_summary(context: str) -> str:
        if "timeout" in context.lower() or "retry" in context.lower():
            return (
                "Likely payment gateway retry fanout regression causing checkout latency and "
                "timeout amplification. "
                "Recommended mock actions remain approval-gated."
            )
        return (
            "Deterministic mock provider found no high-confidence external dependency regression."
        )
