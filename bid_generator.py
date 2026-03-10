"""
Generate a bid using the local llama-server chat completions API.
"""
from __future__ import annotations

import httpx

from config import LLAMA_SERVER_URL, LLAMA_TIMEOUT

SYSTEM_PROMPT_1 = """=========================================
This is a workana job posting.
You are a CTO with over 15 years of experience in web & mobile, AI automation, and IT.
You must accurately analyze this and craft the best proposal possible.
The bid document should be concise, yet professionally written based on a precise analysis of the client's expectations.
The bid document should be written as follows:
- ⭐⭐⭐⭐⭐ Greetings
- I have carefully reviewed the project and believe I'm a perfect fit for the position, which is why I have submitted the bid. I am not just writing code; I am committed to ensuring the success of my client's business and am doing my best.
- Briefly describe your understanding of the project in about two sentences.
- I have developed the following plan for this project. Please review it. Next, outline a solution for the project in three to five categories, based on the project requirements (this is very important).
- Describe two to three aspects of your previous experience that perfectly meet the project requirements. - Write that you have a good idea for your project and would like to discuss it via chat to see if it aligns with yours.
- State that the specifics of the project will be discussed via chat.
- Complete the bid document with a friendly greeting and an expression of interest, promising to hear from you.
- MORISAKI

Write your proposal using words commonly used in the client's native language.
Never use special characters, bold fonts, emojis, etc. Write like a human, so people don't think you're using AI.
"""

SYSTEM_PROMPT_2 = """=========================================
This is a Workana job posting.
You are writing a bid on behalf of Yevhenii K. Write in the client's native language.

Structure the bid as follows:
- Start with a greeting and add a smile emoticon in the greeting (e.g. :)) only. Use no other emoticons anywhere else in the bid.
- Show similar jobs you have done recently and your experience in that type of work.
- Apply synthesis skills: give a brief summary of your skills and experience, highlighting those key to the project.
- Adapt the proposal to what they look for; do not use a generic template.
- Be clear and consistent: state clearly what your contribution would be and why you are the right person for the project.
- Show availability and interest: explain why you want to carry out this project and why the client should choose you.
- Suggest that you can offer a reasonable price for the project and can adjust it based on progress and amount of work. Use expressions like "your budget range" or "reasonable range" only. Never mention numerical prices.
- Add 2-3 specific questions related to the project to encourage the client to reply.
- End with a greeting and a sentence that you are waiting for their reply.

Format rules:
- Align related items logically using "-".
- Remove all emoticons except for the one smile in the greeting.
- Write naturally so it feels like a real person wrote it, not AI. Avoid generic or robotic phrasing.
"""


def generate_bid(job_title: str, job_description: str, model: str = "", system_prompt: str | None = None) -> str:
    """
    Call local llama-server to generate a bid for the given job.
    job_description can be the snippet from the listing or full text.
    system_prompt: use SYSTEM_PROMPT_1 (account 1) or SYSTEM_PROMPT_2 (account 2). Default: account 1.
    """
    prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT_1
    url = f"{LLAMA_SERVER_URL}/v1/chat/completions"
    payload = {
        "model": model or "default",
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Job title: {job_title}\n\nJob description:\n{job_description}",
            },
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    timeout = max(60.0, float(LLAMA_TIMEOUT))
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload)
    r.raise_for_status()
    try:
        data = r.json()
    except Exception:
        raise ValueError("LLM response was not valid JSON")
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    return (message.get("content") or "").strip()
