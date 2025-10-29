import gzip
import json
from typing import Any, Dict

from central_node.control_layer.scheduler_module.scheduler import Scheduler
from shared.custom_exception import NotFoundException
from config import Config


class GetTaxiDRoadsPreprocessedController:
    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler

    def execute(self) -> Dict[str, Any]:
        path = Config.TAXID_ROADS_JSON_GZ_PATH
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            raise NotFoundException(f"Preprocessed roads not found at '{path}'. Run preprocessing first.")
        except Exception as e:
            raise NotFoundException(f"Failed to load preprocessed roads: {e}")

