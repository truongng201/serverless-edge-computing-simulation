class Node {
    constructor(id, x, y, capacity, currentLoad, coverage) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.capacity = capacity; 
        this.currentLoad = currentLoad;
        this.coverage = coverage; 
    }
}

export class Graph {
    constructor() {
        this.nodes = [];
        this.edges = [];
        this.nodeMap = new Map(); // Optional: to quickly access nodes by id
    }

    addNode(node) {
        this.nodes.push(node);
        this.nodeMap.set(node.id, node);
    }

    addEdge(source, target, weight) {
        this.edges.push({ source, target, weight });
    }

    getNodeById(id) {
        return this.nodeMap.get(id);
    }

    getAllNodes() {
        return Array.from(this.nodeMap.values());
    }
}

export class EdgeNode extends Node {
    constructor(id, x, y, capacity, coverage, replicas = [], currentLoad = 0) {
        super(id, x, y, capacity, 0, coverage);
        this.replicas = replicas;
        this.type = 'edge';
        this.currentLoad = currentLoad;
    }
}

export class CentralNode extends Node {
    constructor(id, x, y, capacity, coverage, currentLoad = 0) {
        super(id, x, y, capacity, 0, coverage);
        this.type = 'central';
        this.currentLoad = currentLoad; // Current load of the central node
    }
}

export class UserNode extends Node {
    constructor(id, x, y, capacity, coverage, userSpeed, latency = 0, assignedNode = null, predictedPath = []) {
        super(id, x, y, capacity, 0, coverage);
        this.type = 'user';
        this.userSpeed = userSpeed;
        this.velocity = {
            x: (Math.random() - 0.5) * userSpeed, // Random velocity in x direction
            y: (Math.random() - 0.5) * userSpeed  // Random velocity in y direction
        }
        this.latency = latency; // Latency to the nearest edge node
        this.assignedNode = assignedNode; // Node to which the user is currently connected
        this.predictedPath = predictedPath; // Predicted path for the user
    }
}

export default {
    EdgeNode,
    CentralNode,
    UserNode
}