from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("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"))

chat_completion = client.chat.completions.create(
    model="llama3-8b-8192",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
)

print(chat_completion.choices[0].message.content)
