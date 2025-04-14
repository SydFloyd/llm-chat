import os
import anthropic
from config import cfg

haiku = "claude-3-haiku-20240307"
sonnet = "claude-3-sonnet-20240229"
opus = "claude-3-opus-20240229"

anthropic_client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=cfg.anthropic_api_key,
)

class Claude:
    def __init__(self, 
                 model=haiku, 
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

        self.client = anthropic_client

    def compile_messages(self, prompt):
        messages = []
        if self.injected_messages:
            messages.extend(self.injected_messages)
        if self.save_messages:
            messages.extend(self.message_history)
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def prompt(self, prompt):
        messages = self.compile_messages(prompt)

        if self.system_message:
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                system=self.system_message,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        else:
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        print(response)

        answer = response.content[0].text
        if self.save_messages:
            self.message_history.append({"role": "user", "content": prompt})
            self.message_history.append(answer)

        return answer
    
def list_anthropic_models(limit=20):
    models = anthropic_client.models.list(limit=limit)
    model_mappping = {x.display_name: x.id for x in models.data}
    return model_mappping

if __name__ == "__main__":
    print(list_anthropic_models())
    # m = Claude()
    # print(m.prompt("What did the quick brown fox jump over?"))