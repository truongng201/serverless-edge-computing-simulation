import axios from "axios";
import useGlobalState from "@/hooks/use-global-state";


export const fetchPerformanceMetrics = async () => {
  const { setPerformanceMetrics, setCloudletMetrics } = useGlobalState.getState();
  
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/performance_metrics`
      );
      
      if (response.data && response.data?.status === "success") {
        const data = response.data.data;
        
        // Update performance metrics
        if (data.performance_summary) {
          setPerformanceMetrics({
            algorithm: data.performance_summary.algorithm,
            total_cost: data.performance_summary.performance_metrics.total_cost,
            total_turnaround_time: data.performance_summary.performance_metrics.total_turnaround_time,
            total_migration_cost: data.performance_summary.performance_metrics.total_migration_cost,
            total_cold_start_penalty: data.performance_summary.performance_metrics.total_cold_start_penalty,
            num_users: data.performance_summary.resource_utilization.total_users,
            resource_utilization: data.performance_summary.resource_utilization
          });
        }
        
        // Update cloudlet metrics
        if (data.detailed_cloudlet_metrics) {
          setCloudletMetrics(data.detailed_cloudlet_metrics);
        }
        
        return data;
      }
    }
  } catch (error) {
    console.error("Error fetching performance metrics:", error);
  }
  return null;
};


export const compareAlgorithms = async (userLocation = null) => {
  const { setAlgorithmComparison } = useGlobalState.getState();
  
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/compare_algorithms`,
        userLocation ? { user_location: userLocation } : {}
      );
      
      if (response.data && response.data?.status === "success") {
        const data = response.data.data;
        setAlgorithmComparison(data);
        return data;
      }
    }
  } catch (error) {
    console.error("Error comparing algorithms:", error);
  }
  return null;
};

export const getAlgorithmPerformanceDiff = async () => {
  try {
    if (process.env.NEXT_PUBLIC_API_URL) {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/algorithm_performance_diff`
      );
      
      if (response.data && response.data?.status === "success") {
        return response.data.data;
      }
    }
  } catch (error) {
    console.error("Error fetching algorithm performance diff:", error);
  }
  return null;
};

export const startPerformanceMetricsAutoRefresh = (intervalMs = 5000) => {
  const intervalId = setInterval(() => {
    fetchPerformanceMetrics();
  }, intervalMs);
  
  return intervalId; // Return interval ID so it can be cleared later
};

export const stopPerformanceMetricsAutoRefresh = (intervalId) => {
  if (intervalId) {
    clearInterval(intervalId);
  }
};