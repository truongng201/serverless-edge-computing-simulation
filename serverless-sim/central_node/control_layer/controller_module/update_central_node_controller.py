from central_node.control_layer.scheduler_module.scheduler import Scheduler
from shared import InvalidDataException


class UpdateCentralNodeController:
    def __init__(self, scheduler: Scheduler, data: dict):
        self.scheduler = scheduler
        self.data = data or {}
        self._validate()

    def _validate(self):
        if 'location' not in self.data or not isinstance(self.data['location'], dict):
            raise InvalidDataException("location is required: {'x': <float>, 'y': <float>}")
        loc = self.data['location']
        if 'x' not in loc or 'y' not in loc:
            raise InvalidDataException("location must include x and y")
        if 'coverage' in self.data and self.data['coverage'] is not None:
            try:
                c = float(self.data['coverage'])
                if c < 0:
                    raise InvalidDataException("coverage must be non-negative")
            except Exception:
                raise InvalidDataException("coverage must be a number")

    def _apply(self):
        # Update scheduler's central node dict
        try:
            self.scheduler.central_node['location'] = {
                'x': float(self.data['location']['x']),
                'y': float(self.data['location']['y'])
            }
        except Exception:
            # Fallback: assign raw
            self.scheduler.central_node['location'] = self.data['location']
        if 'coverage' in self.data and self.data['coverage'] is not None:
            self.scheduler.central_node['coverage'] = float(self.data['coverage'])

    def execute(self):
        self._apply()
        return self.scheduler.get_central_node_info()

