from openai import OpenAI
from config import cfg

openai_client = OpenAI(
    api_key = cfg.openai_api_key
)

def list_openai_models():
    return {
        "GPT 3.5": "gpt-3.5-turbo",
        "GPT o3 mini": "o3-mini",
        "GPT o1 mini": "o1-mini",
        "o1 (expensive)": "o1",
        "GPT 4o": "gpt-4o",
    }

class GPT:
    def __init__(self, 
                 model='gpt-3.5-turbo', 
                 max_tokens=1000, 
                 temperature=0.3, 
                 system_message=None, 
                 injected_messages=None,
                 save_messages=False):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_message = system_message
        self.injected_messages = injected_messages
        self.save_messages = save_messages

        self.message_history = []

        self.client = openai_client

    def compile_messages(self, prompt):
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        if self.injected_messages:
            messages.extend(self.injected_messages)
        if self.save_messages:
            messages.extend(self.message_history)
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def prompt(self, prompt):
        messages = self.compile_messages(prompt)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
        )

        answer = response.choices[0].message
        if self.save_messages:
            self.message_history.append({"role": "user", "content": prompt})
            self.message_history.append(answer)
        return answer.content

if __name__ == "__main__":
    m = GPT()
    print(m.prompt("What is the integral of 1/x?"))