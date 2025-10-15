import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Button } from "@/components/ui/button";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogDescription 
} from "@/components/ui/dialog";
import { TrendingUp, Play, Pause, RotateCcw } from "lucide-react";
import useGlobalState from "@/hooks/use-global-state";
import { fetchPerformanceMetrics } from "@/lib/simulation-management";

export default function TATChart() {
  const { performanceMetrics, assignmentAlgorithm, isSimulating } = useGlobalState();
  const [isOpen, setIsOpen] = useState(false);
  const [tatHistory, setTatHistory] = useState([]);
  const [isLiveUpdating, setIsLiveUpdating] = useState(false);
  const intervalRef = useRef(null);
  const startTimeRef = useRef(null);
  const [yAxisDomain, setYAxisDomain] = useState([0, 10000]); // Default range in ms

  // Function to add new data point
  const addDataPoint = (newTat) => {
    const now = new Date();
    if (!startTimeRef.current) {
      startTimeRef.current = now;
    }
    
    const timeElapsed = Math.floor((now - startTimeRef.current) / 1000); // seconds elapsed
    
    const newDataPoint = {
      timestamp: now.toLocaleTimeString(),
      timeElapsed,
      tat: Number(newTat) || 0,
      algorithm: assignmentAlgorithm
    };

    setTatHistory(prev => {
      const updated = [...prev, newDataPoint];
      // Keep only last 50 data points to prevent memory issues
      const finalData = updated.length > 50 ? updated.slice(-50) : updated;
      
      // Update Y-axis domain based on data
      if (finalData.length > 0) {
        const values = finalData.map(d => d.tat);
        const minVal = Math.min(...values);
        const maxVal = Math.max(...values);
        const padding = (maxVal - minVal) * 0.1 || 1000; // 10% padding or 1000ms minimum
        setYAxisDomain([
          Math.max(0, Math.floor(minVal - padding)), 
          Math.ceil(maxVal + padding)
        ]);
      }
      
      return finalData;
    });
  };

  // Start live updates
  const startLiveUpdating = () => {
    if (!startTimeRef.current) {
      startTimeRef.current = new Date();
    }
    
    setIsLiveUpdating(true);
    intervalRef.current = setInterval(async () => {
      // Only fetch if simulation is running
      if (isSimulating) {
        try {
          await fetchPerformanceMetrics();
          // The performanceMetrics will be updated via useGlobalState
        } catch (error) {
          console.error('Error fetching performance metrics:', error);
        }
      }
    }, 2000); // Update every 2 seconds
  };

  // Stop live updates
  const stopLiveUpdating = () => {
    setIsLiveUpdating(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Clear history and reset
  const clearHistory = () => {
    setTatHistory([]);
    startTimeRef.current = null;
    stopLiveUpdating();
  };

  // Effect to sync with simulation state
  useEffect(() => {
    if (isSimulating && !isLiveUpdating) {
      // Auto start when simulation begins
      startLiveUpdating();
    } else if (!isSimulating && isLiveUpdating) {
      // Auto stop when simulation ends
      stopLiveUpdating();
    }
  }, [isSimulating]);

  // Effect to add data when performanceMetrics changes during live updates
  useEffect(() => {
    if (isLiveUpdating && isSimulating && performanceMetrics?.total_turnaround_time !== undefined) {
      addDataPoint(performanceMetrics.total_turnaround_time);
    }
  }, [performanceMetrics?.total_turnaround_time, isLiveUpdating, isSimulating]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Custom tooltip formatter
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded shadow-lg">
          <p className="text-sm font-medium">{`Time: ${label}`}</p>
          <p className="text-sm text-blue-600">
            {`TAT: ${payload[0].value}ms`}
          </p>
          <p className="text-xs text-gray-500">
            {`Algorithm: ${payload[0].payload.algorithm}`}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
          <TrendingUp className="w-3 h-3 mr-1" />
          Chart
        </Button>
      </DialogTrigger>
            <DialogContent className="max-w-6xl w-full h-[85vh] p-4 flex flex-col">
        <DialogHeader className="pb-2 flex-shrink-0">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="w-4 h-4" />
            Total Turnaround Time (TAT) Over Time
          </DialogTitle>
          <DialogDescription className="text-sm">
            Real-time visualization of Total Turnaround Time using {assignmentAlgorithm} algorithm
            {!isSimulating && " (Simulation stopped - chart updates paused)"}
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex-1 flex flex-col min-h-0">
          {/* Controls */}
          <div className="flex items-center gap-2 mb-3 p-3 bg-gray-50 rounded-lg flex-shrink-0">
            <Button
              onClick={isLiveUpdating ? stopLiveUpdating : startLiveUpdating}
              variant={isLiveUpdating ? "destructive" : "default"}
              size="sm"
              disabled={!isSimulating && !isLiveUpdating}
            >
              {isLiveUpdating ? (
                <>
                  <Pause className="w-4 h-4 mr-2" />
                  Stop Updates
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Start Updates
                </>
              )}
            </Button>
            
            <Button onClick={clearHistory} variant="outline" size="sm">
              <RotateCcw className="w-4 h-4 mr-2" />
              Clear History
            </Button>
            
            <div className="flex items-center gap-2 text-sm text-gray-600 ml-auto">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span>TAT: {performanceMetrics?.total_turnaround_time || 0}ms</span>
              </div>
              <span>•</span>
              <span>Algorithm: {assignmentAlgorithm}</span>
              <span>•</span>
              <span>Data Points: {tatHistory.length}</span>
              <span>•</span>
              <div className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${isSimulating ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className={isSimulating ? 'text-green-600' : 'text-red-600'}>
                  {isSimulating ? 'Simulation Running' : 'Simulation Stopped'}
                </span>
              </div>
              {isLiveUpdating && isSimulating && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-blue-600">Updating</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Chart */}
          <div className="flex-1 min-h-0 bg-white rounded-lg border">
            {tatHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={tatHistory}
                  margin={{
                    top: 20,
                    right: 30,
                    left: 50,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis 
                    dataKey="timestamp" 
                    tick={{ fontSize: 11 }}
                    interval="preserveStartEnd"
                    axisLine={{ stroke: '#e0e0e0' }}
                    tickLine={{ stroke: '#e0e0e0' }}
                  />
                  <YAxis 
                    domain={yAxisDomain}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => `${value}ms`}
                    axisLine={{ stroke: '#e0e0e0' }}
                    tickLine={{ stroke: '#e0e0e0' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="tat" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
                    activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#ffffff' }}
                    name="Total Turnaround Time (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <TrendingUp className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg mb-2">No data available</p>
                  <p className="text-sm">
                    {isSimulating ? 
                      'Data collection will begin automatically...' : 
                      'Start the simulation to begin collecting TAT data'
                    }
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Statistics */}
          {tatHistory.length > 1 && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg flex-shrink-0">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Current TAT:</span>
                  <div className="font-mono font-semibold">
                    {tatHistory[tatHistory.length - 1]?.tat || 0}ms
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Average TAT:</span>
                  <div className="font-mono font-semibold">
                    {Math.round(tatHistory.reduce((sum, point) => sum + point.tat, 0) / tatHistory.length)}ms
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Min TAT:</span>
                  <div className="font-mono font-semibold">
                    {Math.min(...tatHistory.map(p => p.tat))}ms
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">Max TAT:</span>
                  <div className="font-mono font-semibold">
                    {Math.max(...tatHistory.map(p => p.tat))}ms
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}