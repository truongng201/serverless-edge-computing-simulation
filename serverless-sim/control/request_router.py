from exceution.handler_api import HandlerAPI

class RequestRouter:
    def __init__(self, scheduler):
        self.scheduler = scheduler

    def route(self, req_id):
        edge = self.scheduler.schedule_request(req_id)
        if edge:
            api = HandlerAPI(edge)
            api.process_request(req_id)
        else:
            print(f"[Router] No available edge node for request {req_id}")
