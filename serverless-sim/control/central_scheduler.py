class CentralControl:
    def __init__(self, edge_nodes):
        self.edge_nodes = edge_nodes


    def schedule_request(self, req_id):
        for edge in self.edge_nodes:
            if edge.is_available():
                return edge
        return None
    
    
    def metrics_collector(self):
        pass
