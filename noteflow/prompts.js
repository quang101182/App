// NoteFlow v1.2.7 — Prompts IA
const NF_PROMPTS = {

  meeting_summary: (lang) => `You are a professional meeting notes assistant. Analyze the following transcript and produce a structured JSON summary.

IMPORTANT: Respond ONLY with valid JSON, no markdown, no explanation.

CRITICAL — Output language: ALL text values in the JSON MUST be written in ${lang}. Do NOT use English unless the output language IS English. This applies to title, overview, key_points, decisions, action_items, follow_up, and all other text fields.

JSON structure:
{
  "title": "Short descriptive meeting title",
  "date": "Date if mentioned, or null",
  "duration": "Estimated duration from timestamps",
  "participants": ["Speaker 1", "Speaker 2"],
  "overview": "2-3 sentence summary of the meeting",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "decisions": ["Decision 1", "Decision 2"],
  "action_items": [
    {"owner": "Speaker name or null", "task": "What needs to be done", "deadline": "If mentioned or null"}
  ],
  "follow_up": ["Topics to revisit", "Open questions"],
  "sentiment": "Overall tone: positive/neutral/concerned/mixed"
}

Rules:
- Extract ALL action items with assigned owners when possible
- Keep key_points concise but informative
- If no decisions were made, use empty array
- Identify follow-up items and open questions
- Be factual, do not invent information not in the transcript`,

  refine_summary: (instruction) => `Refine the following meeting summary based on this instruction: "${instruction}"
Keep the same JSON structure. Respond ONLY with valid JSON.`

};

if (typeof window !== 'undefined') window.NF_PROMPTS = NF_PROMPTS;
