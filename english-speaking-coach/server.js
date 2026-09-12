const express = require('express');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5';

async function translateWithClaude(thaiText) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: ANTHROPIC_MODEL,
      max_tokens: 200,
      system:
        'You help a Thai speaker practice conversational English. ' +
        'The user writes, in Thai, something they want to know how to say in English. ' +
        'Reply with ONLY the single most natural, commonly-used spoken English sentence for that situation. ' +
        'No quotes, no explanation, no alternatives, no Thai text in the reply.',
      messages: [{ role: 'user', content: thaiText }],
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Anthropic API error ${res.status}: ${body.slice(0, 200)}`);
  }
  const data = await res.json();
  const text = data?.content?.[0]?.text?.trim();
  if (!text) throw new Error('Anthropic API returned no text');
  return text;
}

async function translateWithMyMemory(thaiText) {
  const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(thaiText)}&langpair=th|en`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`MyMemory API error: ${res.status}`);
  const data = await res.json();
  const text = data?.responseData?.translatedText;
  if (!text) throw new Error('MyMemory API returned no translation');
  return text;
}

app.post('/api/translate', async (req, res) => {
  const text = req.body?.text;
  if (!text || typeof text !== 'string' || !text.trim()) {
    return res.status(400).json({ error: 'ไม่มีข้อความให้แปล' });
  }
  try {
    const engine = ANTHROPIC_API_KEY ? 'claude' : 'mymemory';
    const english = ANTHROPIC_API_KEY
      ? await translateWithClaude(text.trim())
      : await translateWithMyMemory(text.trim());
    res.json({ english, engine });
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ ok: true, engine: ANTHROPIC_API_KEY ? 'claude' : 'mymemory' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`English speaking coach running at http://localhost:${PORT}`);
  console.log(`Translation engine: ${ANTHROPIC_API_KEY ? 'Claude API' : 'MyMemory (free, no key)'}`);
});
