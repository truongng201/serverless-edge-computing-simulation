import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const getClusterStatusAndUsersData = async () => {
  const {
    setCentralNodes,
    setEdgeNodes,
    setUsers,
    setLoadingData,
    setDataError,
    setLiveData,
    edgeCoverage,
    centralCoverage,
    userSize
  } = useGlobalState.getState();
  try {
    setLoadingData(true);
    const [clusterResponse, usersResponse] = await Promise.all([
      axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/cluster/status`
      ),
      axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_all_users`
      ),
    ]);

    if (clusterResponse.data && clusterResponse.data.success) {
      setLiveData(clusterResponse.data);

      const realCentralNode = {
        id: clusterResponse.data.central_node.id || "central_node",
        x: clusterResponse.data.central_node.location.x || 600,
        y: clusterResponse.data.central_node.location.y || 400,
        coverage:
          clusterResponse.data.central_node.coverage || centralCoverage[0],
        currentLoad: clusterResponse.data.central_node.cpu_usage || 0,
      };
      setCentralNodes([realCentralNode]);

      const realEdgeNodes = (
        clusterResponse.data.cluster_info.edge_nodes_info || []
      ).map((node, index) => ({
        id: node.node_id || `edge_${index}`,
        x: node.location.x || 100 + index * 100,
        y: node.location.y || 200 + index * 100,
        coverage: node.coverage || edgeCoverage[0],
        currentLoad: node.metrics.cpu_usage || 0,
      }));
      setEdgeNodes(realEdgeNodes);
    }

    // Update users if available
    if (
      usersResponse.data &&
      usersResponse.data.success &&
      usersResponse.data.users
    ) {
      const realUsers = usersResponse.data.users.map((user, index) => ({
        id: user.user_id || `user_${index}`,
        x: user.location.x || 0,
        y: user.location.y || 0,
        vx: 0,
        vy: 0,
        assignedEdge: user.assigned_edge || null,
        assignedCentral: user.assigned_central || null,
        assignedNodeID: user.assigned_node_id || null,
        latency: user.latency || 0,
        size: user.size || userSize[0] || 10,
        last_executed_period: user.last_executed_period || null,
      }));
      setUsers(realUsers);
    }
  } catch (error) {
    setDataError(`Error getting cluster and users data: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
