import random

class AdversarialPromptGenerator:
    def __init__(self, categories, strategy_lib, templates):
        self.categories = categories
        self.strategy_lib = strategy_lib
        self.templates = templates

    def generate_prompt(self, category_name: str) -> str:
        category = self.categories[category_name]

        chosen_strategies = random.sample(
            category.strategies,
            k=min(2, len(category.strategies))
        )

        fragments = {
            "role": random.choice(self.strategy_lib.get("role_play", [""])),
            "override": random.choice(self.strategy_lib.get("instruction_override", [""])),
            "scenario": random.choice(self.strategy_lib.get("hypothetical_scenario", [""])),
            "constraints": random.choice(self.strategy_lib.get("constraints", [""])),
            "tone": random.choice(self.strategy_lib.get("tone", [""])),
            "format": random.choice(self.strategy_lib.get("output_format", [""])),
            "objective": random.choice(category.goal)
        }

        template = random.choice(self.templates)
        return template.format(**fragments)

    def generate_batch(self, category_name: str, n: int = 10):
        return [self.generate_prompt(category_name) for _ in range(n)]
