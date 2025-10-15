import random


class RandomGeneratedDataLoader:
    """Generates and manages random data for simulation"""
    def __init__(self, num_items: int = 100):
        self.data = [{"id": i, "value": random.random()} for i in range(num_items)]

    def get_data_by_step(self, step: int):
        return self.data