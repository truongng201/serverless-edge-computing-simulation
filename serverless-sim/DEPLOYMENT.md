# Serverless Edge Computing Simulation - Deployment Guide

This guide explains how to deploy the serverless edge computing simulation across multiple computers within the same network.

## Architecture Overview

```
┌─────────────────┐    Network    ┌─────────────────┐
│  Central Node   │◄──────────────►│   Edge Node 1   │
│  (Computer A)   │               │  (Computer B)   │
│                 │               │                 │
│ • Control Layer │               │ • API Layer     │
│ • API Layer     │               │ • Resource Layer│
│ • Resource Layer│               │                 │
│ • Simulation UI │               │                 │
└─────────────────┘               └─────────────────┘
         ▲                                ▲
         │                                │
         ▼                                ▼
┌─────────────────┐               ┌─────────────────┐
│   Edge Node 2   │               │   Edge Node N   │
│  (Computer C)   │               │  (Computer N)   │
└─────────────────┘               └─────────────────┘
```

## Prerequisites

### All Computers

- Python 3.8 or higher
- pip3 package manager
- Docker installed and running
- Network connectivity between all machines

### Network Requirements

- All computers must be on the same network
- Firewall should allow communication on configured ports
- Default ports: 5001 (central), 5002+ (edge nodes)

## Deployment Steps

### Step 1: Deploy Central Node

1. **Choose the central computer** (usually the most powerful one)

2. **Get the central computer's IP address:**

   ```bash
   # On Linux/macOS
   hostname -I | awk '{print $1}'
   
   # On Windows
   ipconfig | findstr IPv4
   ```

3. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd Serverless-edge-computing-simulation/serverless-sim
   ```

4. **Configure central node (optional):**

   ```bash
   cp central_config.env.example central_config.env
   # Edit central_config.env with your preferred settings
   ```

5. **Deploy central node:**

   ```bash
   # Simple deployment
   ./deploy_central.sh
   
   # Custom configuration
   HOST=0.0.0.0 PORT=5001 ./deploy_central.sh
   ```

6. **Verify central node is running:**

   ```bash
   curl http://<CENTRAL_IP>:5001/api/v1/central/health
   ```

### Step 2: Deploy Edge Nodes

Repeat these steps on each computer that will run an edge node:

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd Serverless-edge-computing-simulation/serverless-sim
   ```

2. **Configure edge node (optional):**

   ```bash
   cp edge_config.env.example edge_config.env
   # Edit edge_config.env with your settings
   ```

3. **Deploy edge node:**

   ```bash
   # Required: node ID and central URL
   ./deploy_edge.sh --node-id edge_lab1 --central-url http://<CENTRAL_IP>:5001
   
   # With custom port
   ./deploy_edge.sh --node-id edge_lab2 --central-url http://<CENTRAL_IP>:5001 --port 5003
   
   # Using environment variables
   NODE_ID=edge_office1 CENTRAL_URL=http://192.168.1.100:5001 ./deploy_edge.sh
   ```

4. **Verify edge node registration:**

   ```bash
   curl http://<CENTRAL_IP>:5001/api/v1/central/cluster/status
   ```

## Configuration Examples

### Example 1: Lab Environment

```bash
# Central Node (Lab Computer 1 - 192.168.1.100)
./deploy_central.sh

# Edge Node 1 (Lab Computer 2 - 192.168.1.101)
./deploy_edge.sh --node-id lab_comp2 --central-url http://192.168.1.100:5001

# Edge Node 2 (Lab Computer 3 - 192.168.1.102)
./deploy_edge.sh --node-id lab_comp3 --central-url http://192.168.1.100:5001
```

### Example 2: Office Environment with Custom Ports

```bash
# Central Node (Main Server - 10.0.0.50)
PORT=8001 ./deploy_central.sh

# Edge Node 1 (Workstation 1 - 10.0.0.51)
./deploy_edge.sh --node-id office_ws1 --central-url http://10.0.0.50:8001 --port 8002

# Edge Node 2 (Workstation 2 - 10.0.0.52)
./deploy_edge.sh --node-id office_ws2 --central-url http://10.0.0.50:8001 --port 8003
```

## Access Points

### Central Node

- **Simulation UI**: `http://<CENTRAL_IP>:5001`
- **Central API**: `http://<CENTRAL_IP>:5001/api/v1/central`
- **Cluster Status**: `http://<CENTRAL_IP>:5001/api/v1/central/cluster/status`
- **Health Check**: `http://<CENTRAL_IP>:5001/api/v1/central/health`

### Edge Nodes

- **Node Status**: `http://<EDGE_IP>:<EDGE_PORT>/api/v1/edge/status`
- **Health Check**: `http://<EDGE_IP>:<EDGE_PORT>/api/v1/edge/health`
- **Execute Function**: `http://<EDGE_IP>:<EDGE_PORT>/api/v1/edge/execute`

## Testing the Deployment

### 1. Check Cluster Status

```bash
curl http://<CENTRAL_IP>:5001/api/v1/central/cluster/status | jq
```

### 2. Execute a Function

```bash
curl -X POST http://<CENTRAL_IP>:5001/api/v1/central/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "function_id": "test_function",
    "payload": {"message": "Hello from distributed cluster!"}
  }'
```

### 3. Monitor Metrics

```bash
# Get cluster metrics
curl http://<CENTRAL_IP>:5001/api/v1/central/metrics/export?duration_hours=1

# Get individual edge node status
curl http://<EDGE_IP>:<EDGE_PORT>/api/v1/edge/status
```

## Troubleshooting

### Common Issues

1. **Edge node cannot connect to central node:**
   - Check if central node is running
   - Verify IP address and port
   - Check firewall settings
   - Test with: `curl http://<CENTRAL_IP>:5001/api/v1/central/health`

2. **Docker permission errors:**

   ```bash
   # Add user to docker group (Linux)
   sudo usermod -aG docker $USER
   # Log out and log back in
   ```

3. **Port already in use:**
   - Use auto-port detection: don't specify `--port`
   - Or specify a different port: `--port 5010`

4. **Module import errors:**
   - Ensure you're in the correct directory
   - Check Python path: `python3 -c "import sys; print(sys.path)"`

### Logs and Monitoring

- **Central Node**: Check `central_node.log`
- **Edge Nodes**: Check `<node_id>.log`
- **Real-time monitoring**: Use the simulation UI at `http://<CENTRAL_IP>:5001`

### Performance Tips

1. **For better performance:**
   - Use dedicated machines for central node
   - Ensure sufficient RAM and CPU on edge nodes
   - Use SSD storage for Docker containers

2. **For large deployments:**
   - Increase Docker resource limits
   - Adjust metrics collection intervals
   - Configure load balancing strategies

## Security Considerations

### For Production Deployments

1. **Enable authentication:**
   - Configure API keys in environment files
   - Use HTTPS/TLS for communication

2. **Network security:**
   - Use VPN for remote edge nodes
   - Configure proper firewall rules
   - Limit API access to authorized networks

3. **Container security:**
   - Use trusted container images
   - Enable Docker security features
   - Regular security updates

## Advanced Configuration

### Environment Variables

You can override any configuration using environment variables:

```bash
# Central Node
export CENTRAL_HOST=0.0.0.0
export CENTRAL_PORT=5001
export LOG_LEVEL=DEBUG
./deploy_central.sh

# Edge Node
export NODE_ID=production_edge_1
export CENTRAL_URL=http://10.0.0.100:5001
export LOG_LEVEL=INFO
./deploy_edge.sh
```

### Custom Docker Images

To use custom function images:

1. Build your images on each edge node
2. Update configuration:

   ```bash
   # In edge_config.env
   DEFAULT_CONTAINER_IMAGE=my-custom-image:latest
   ```

This deployment guide enables you to set up a distributed serverless edge computing simulation across multiple computers within your network.
