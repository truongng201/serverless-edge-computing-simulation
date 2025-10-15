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
        if (data) {
          setPerformanceMetrics({
            total_turnaround_time: data.total_turnaround_time,
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

