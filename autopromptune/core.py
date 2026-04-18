"""
core.py
=======
Orchestrates the two-pass prompt tuning pipeline.

Pass 1 — Identify vague terms (identify_vague.j2)
Pass 2 — Rewrite the prompt            (tune_prompt.j2)

Part of MSc AI thesis research — Eduardo J. Barrios (@edujbarrios)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .llm_client import LLMClient

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class VagueTerm:
    """A single vague term identified in the original prompt."""

    term: str
    reason: str
    replacement: str


@dataclass
class TuningResult:
    """Full result returned by :class:`PromptTuner`."""

    original_prompt: str
    tuned_prompt: str
    vague_terms: List[VagueTerm] = field(default_factory=list)

    @property
    def was_changed(self) -> bool:
        return self.original_prompt.strip() != self.tuned_prompt.strip()

    def summary(self) -> str:
        lines = [
            "=== AutoPromTune Result ===",
            f"Original : {self.original_prompt}",
            f"Tuned    : {self.tuned_prompt}",
            "",
        ]
        if self.vague_terms:
            lines.append(f"Identified {len(self.vague_terms)} vague term(s):")
            for vt in self.vague_terms:
                lines.append(f'  • "{vt.term}" → "{vt.replacement}"')
                lines.append(f'    Reason: {vt.reason}')
        else:
            lines.append("No vague terms found — prompt was already precise.")
        return "\n".join(lines)


class PromptTuner:
    """Two-pass LLM-based prompt disambiguation engine.

    Usage::

        tuner = PromptTuner()
        result = tuner.tune("Describe if there is a blue ball on the image")
        print(result.tuned_prompt)
    """

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client or LLMClient()
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape([]),  # plain text templates
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tune(self, prompt: str) -> TuningResult:
        """Run the full two-pass tuning pipeline on *prompt*.

        Returns a :class:`TuningResult` with the improved prompt and a
        structured list of every vague term that was replaced.
        """
        logger.info("AutoPromTune — pass 1: identifying vague terms …")
        vague_terms = self._identify_vague_terms(prompt)

        logger.info(
            "AutoPromTune — pass 2: rewriting prompt (%d vague term(s)) …",
            len(vague_terms),
        )
        tuned = self._rewrite_prompt(prompt, vague_terms)

        return TuningResult(
            original_prompt=prompt,
            tuned_prompt=tuned,
            vague_terms=vague_terms,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_template(self, template_name: str, **kwargs: object) -> str:
        tpl = self._jinja_env.get_template(template_name)
        return tpl.render(**kwargs)

    def _identify_vague_terms(self, prompt: str) -> List[VagueTerm]:
        """Stage 1: ask the LLM to return a JSON list of vague terms."""
        system_prompt = self._render_template("identify_vague.j2")
        raw = self._client.complete(system_prompt=system_prompt, user_message=prompt)

        # Strip accidental markdown fences the model may include
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning(
                "LLM returned non-JSON in stage 1; treating as no vague terms.\n%s",
                raw,
            )
            return []

        terms: List[VagueTerm] = []
        for item in data.get("vague_terms", []):
            try:
                terms.append(
                    VagueTerm(
                        term=str(item["term"]),
                        reason=str(item["reason"]),
                        replacement=str(item["replacement"]),
                    )
                )
            except (KeyError, TypeError):
                logger.warning("Skipping malformed vague term entry: %r", item)

        return terms

    def _rewrite_prompt(self, original: str, vague_terms: List[VagueTerm]) -> str:
        """Stage 2: ask the LLM to rewrite the prompt with precise terms."""
        user_message = self._render_template(
            "tune_prompt.j2",
            original_prompt=original,
            vague_terms=[
                {"term": vt.term, "reason": vt.reason, "replacement": vt.replacement}
                for vt in vague_terms
            ],
        )
        # The tune template is used as the *user* message; system sets the role.
        system_prompt = (
            "You are an expert prompt engineer specializing in creating clear, precise, "
            "and unambiguous prompts for AI systems. Follow the rewriting instructions exactly. "
            "Output only the refined prompt text with no additional commentary or formatting."
        )
        return self._client.complete(
            system_prompt=system_prompt, user_message=user_message
        )
