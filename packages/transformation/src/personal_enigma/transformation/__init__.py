"""Enigma transformation — private records to sanitised context."""

from personal_enigma.transformation.attention_context import (
    AttentionCandidateInput,
    build_remote_attention_context,
    candidate_input_from_observation,
)
from personal_enigma.transformation.context_relations import with_relations
from personal_enigma.transformation.passages import extract_minimal_passage
from personal_enigma.transformation.protocol import EnigmaTransformer, TransformedContext
from personal_enigma.transformation.relation_inference import infer_relations_from_evidence
from personal_enigma.transformation.relations import SemanticRelation, merge_relations
from personal_enigma.transformation.semantic_preservation import assert_semantic_preservation
from personal_enigma.transformation.stub_resolver import StubHmacResolver
from personal_enigma.transformation.title_sanitisation import pseudonymise_remote_text
from personal_enigma.transformation.transformer import DefaultEnigmaTransformer

__all__ = [
    "AttentionCandidateInput",
    "DefaultEnigmaTransformer",
    "EnigmaTransformer",
    "SemanticRelation",
    "StubHmacResolver",
    "TransformedContext",
    "assert_semantic_preservation",
    "build_remote_attention_context",
    "candidate_input_from_observation",
    "extract_minimal_passage",
    "infer_relations_from_evidence",
    "merge_relations",
    "pseudonymise_remote_text",
    "with_relations",
]
