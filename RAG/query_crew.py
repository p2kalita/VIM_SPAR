import logging
from typing import Optional

from crewai import Agent, Crew, Process, Task
from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from store import GEMINI_MODEL, TOP_K, format_chunks_for_context, retrieve_chunks

logger = logging.getLogger(__name__)


def build_synthesis_agent() -> Agent:
    return Agent(
        role="Invoice Answer Synthesizer",
        goal="Answer the user's invoice question using only the retrieved context chunks.",
        backstory="You are a financial document analyst who answers questions from invoice data.",
        tools=[],
        llm=f"gemini/{GEMINI_MODEL}",
        verbose=True,
        allow_delegation=False,
    )


def build_synthesis_task(agent: Agent, query: str, tenant_id: str, context_text: str = "") -> Task:
    return Task(
        description=(
            f"You are analyzing invoices for vendor: {tenant_id}.\n\n"
            f"RETRIEVED INVOICE CONTEXT (Filtered strictly for {tenant_id}):\n"
            f"{context_text}\n\n"
            f"USER QUESTION:\n"
            f"{query}\n\n"
            f"Instructions:\n"
            f"- Answer the question using ONLY the retrieved invoice context above.\n"
            f"- Cite the relevant invoice number(s).\n"
            f"- If the answer is not present in the context, state clearly that no matching information was found for this vendor."
        ),
        expected_output="A concise, grounded answer citing the relevant invoice number(s).",
        agent=agent,
    )


class QueryCrew:
    """Executes grounded synthesis for tenant queries with retry handling."""

    def __init__(self) -> None:
        self._agent = build_synthesis_agent()

    def _prepare(self, tenant_id: str, query: str, invoice_number: Optional[str], top_k: int):
        chunks = retrieve_chunks(tenant_id=tenant_id, query=query, invoice_number=invoice_number, top_k=top_k)
        context_text = format_chunks_for_context(chunks)
        task = build_synthesis_task(self._agent, query=query, tenant_id=tenant_id, context_text=context_text)
        crew = Crew(agents=[self._agent], tasks=[task], process=Process.sequential, verbose=True)
        return crew, chunks

    def _fallback(self, tenant_id: str, chunks: list, err: Exception) -> str:
        if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
            if chunks:
                best = chunks[0]
                return (
                    f"⚠️ **Note: Gemini Free-Tier rate limit reached.**\n\n"
                    f"**Direct Extracted Invoice Data for `{tenant_id}`:**\n\n"
                    f"> **Invoice:** {best.get('invoice_number')}\n"
                    f"> **Vendor:** {tenant_id}\n\n"
                    f"{best.get('text')}\n\n"
                    f"*(Please wait ~30-60 seconds for the quota window to reset, or update your API key in `.env`)*"
                )
            return f"No invoice chunks found for vendor '{tenant_id}' matching this query."
        return f"Agent execution note: {err}"

    def run(self, tenant_id: str, query: str, invoice_number: Optional[str] = None, top_k: int = TOP_K) -> str:
        crew, chunks = self._prepare(tenant_id, query, invoice_number, top_k)
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential_jitter(initial=2, max=8),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    return str(crew.kickoff())
        except Exception as e:
            return self._fallback(tenant_id, chunks, e)

    async def run_async(self, tenant_id: str, query: str, invoice_number: Optional[str] = None, top_k: int = TOP_K) -> str:
        crew, chunks = self._prepare(tenant_id, query, invoice_number, top_k)
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential_jitter(initial=2, max=8),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    result = await crew.kickoff_async()
                    return str(result)
        except Exception as e:
            return self._fallback(tenant_id, chunks, e)
