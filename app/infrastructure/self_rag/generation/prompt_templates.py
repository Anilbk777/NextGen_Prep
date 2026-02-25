"""
self_RAG/generation/prompt_templates.py

All ChatPromptTemplates for the Self-RAG pipeline in one place.
No prompt string is ever hardcoded inside a chain or class —
every prompt lives here, is named, and has an explicit variable list.

Prompts are grouped by pipeline role:
    Critic prompts    : RETRIEVAL_DECISION, RELEVANCE_CHECK,
                        HALLUCINATION_CHECK, USEFULNESS_SCORE
    Generator prompts : ANSWER_WITH_CONTEXT, ANSWER_WITHOUT_CONTEXT
    Rewriter prompts  : QUERY_REWRITE

Design principles
-----------------
1. Every prompt is a ChatPromptTemplate — compatible with any
   LangChain chat model (OpenAI, Ollama, Anthropic, etc.)

2. Variable names match exactly what critic.py, generator.py,
   and query_rewriter.py pass to chain.invoke({...}).

3. System messages establish the model's role clearly — this
   significantly improves output consistency across models.

4. Output format instructions are explicit and minimal —
   critic prompts ask for a single controlled token, not prose.

5. Prompts are tuned to be robust to model verbosity —
   "Reply ONLY with..." prevents preamble and explanation
   bleeding into the token the output parser receives.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Critic Prompts
# ---------------------------------------------------------------------------

RETRIEVAL_DECISION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a retrieval decision classifier for a RAG (Retrieval-Augmented Generation) pipeline.

Your sole job is to decide whether the given query requires retrieving external documents to answer accurately.

Rules:
- Reply YES if the query requires specific facts, recent information, domain knowledge, named entities, statistics, or details that may not be in general training data.
- Reply NO if the query can be answered accurately and completely from general knowledge alone (basic definitions, simple maths, well-known facts, conversational responses).
- When in doubt, reply YES. It is always safer to retrieve than to hallucinate.

Reply ONLY with the single word: yes or no.
Do not explain. Do not add punctuation.""",
    ),
    (
        "human",
        "Query: {query}",
    ),
])


RELEVANCE_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a document relevance classifier for a RAG pipeline.

Your sole job is to decide whether the provided document passage is relevant to answering the given query.

Rules:
- Reply 'relevant' if the passage contains information that would help answer the query, even partially.
- Reply 'irrelevant' if the passage is off-topic, too general, or contains no useful information for the query.
- Base your decision only on the content of the passage — do not infer from the source or filename.
- When in doubt, reply 'irrelevant'. It is better to discard a borderline passage than to generate from noise.

Reply ONLY with one of: relevant  or  irrelevant
Do not explain. Do not add punctuation.""",
    ),
    (
        "human",
        "Query: {query}\n\nDocument passage:\n{document}",
    ),
])


HALLUCINATION_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a factual grounding classifier for a RAG pipeline.

Your sole job is to determine whether the provided answer is supported by the provided document passage.

Definitions:
- fully_supported   : Every factual claim in the answer can be directly verified from the passage.
- partially_supported: Some but not all factual claims in the answer are supported by the passage.
- not_supported     : The answer contains claims that are absent from or contradict the passage.

Rules:
- Evaluate grounding strictly. If the answer introduces any fact not present in the passage, it is at most partially_supported.
- Ignore writing style, grammar, or completeness — only evaluate factual grounding.
- When in doubt between fully and partially, choose partially_supported.
- When in doubt between partially and not_supported, choose not_supported.

Reply ONLY with one of: fully_supported  or  partially_supported  or  not_supported
Do not explain. Do not add punctuation.""",
    ),
    (
        "human",
        "Answer to evaluate:\n{answer}\n\nSource document passage:\n{document}",
    ),
])


USEFULNESS_SCORE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an answer quality evaluator for a RAG pipeline.

Your sole job is to rate how well the provided answer addresses the given query.

Scoring guide:
1 - Poor       : The answer does not address the query at all, is off-topic, or is empty.
2 - Weak       : The answer is tangentially related but does not actually answer the query.
3 - Average    : The answer partially addresses the query but is incomplete or vague.
4 - Good       : The answer addresses the query well with only minor gaps or imprecision.
5 - Excellent  : The answer fully and precisely addresses the query with appropriate detail.

Rules:
- Score based on how well the query is answered, not on writing quality or length.
- A concise accurate answer scores higher than a long vague one.
- If the answer says it cannot find the information, score 1.

Reply ONLY with a single integer: 1, 2, 3, 4, or 5
Do not explain. Do not add any other text.""",
    ),
    (
        "human",
        "Query: {query}\n\nAnswer to evaluate:\n{answer}",
    ),
])


# ---------------------------------------------------------------------------
# Generator Prompts
# ---------------------------------------------------------------------------

ANSWER_WITH_CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a precise and reliable question-answering assistant.

Answer the query using ONLY the information provided in the context below.

Rules:
- Do not use any prior knowledge or information not present in the context.
- If the context does not contain enough information to answer the query fully, say exactly what you can answer and clearly state what is missing.
- Do not fabricate facts, statistics, names, or dates.
- Be concise and direct. Do not pad the answer with unnecessary explanation.
- Write in clear, professional prose.""",
    ),
    (
        "human",
        "Query: {query}\n\nContext:\n{context}\n\nAnswer:",
    ),
])


ANSWER_WITHOUT_CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a precise and reliable question-answering assistant.

Answer the query directly using your knowledge.

Rules:
- Be concise and direct.
- If you are uncertain about any fact, say so explicitly.
- Do not fabricate specific statistics, citations, or named entities you are not certain about.
- Write in clear, professional prose.""",
    ),
    (
        "human",
        "Query: {query}\n\nAnswer:",
    ),
])


# ---------------------------------------------------------------------------
# Query Rewriter Prompt
# ---------------------------------------------------------------------------

QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a query optimisation specialist for a RAG (Retrieval-Augmented Generation) pipeline.

The pipeline retrieved documents and generated an answer, but the answer was judged to be insufficient.
Your job is to rewrite the original query to retrieve better, more relevant documents on the next attempt.

Rewriting strategies (apply based on attempt number):
- Attempt 1 : Add specificity — include more keywords, domain terms, or context from the query.
- Attempt 2 : Decompose — break the query into a more focused sub-question targeting the core information gap.
- Attempt 3 : Rephrase — use alternative terminology or synonyms that may match document vocabulary better.
- Attempt 4 : Broaden — slightly relax the query to widen the retrieval scope.
- Attempt 5 : Simplify — strip the query to its absolute core to maximise recall.

Rules:
- Output ONLY the rewritten query. No explanation, no preamble, no punctuation at the end.
- The rewritten query must be meaningfully different from the original.
- Preserve the original intent — do not change what the user is asking for.""",
    ),
    (
        "human",
        """Original query: {query}

Previous answer (insufficient): {failed_answer}

Revision attempt: {attempt} of {max_attempts}

Rewritten query:""",
    ),
])