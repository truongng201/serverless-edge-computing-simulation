import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CurrentAlgorithmCard({
  models,
  selectedModel,
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Current Algorithm</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-sm">
          <div className="font-medium mb-2">{models[selectedModel]}</div>
          <div className="text-xs text-gray-600">
            {selectedModel === "lstm" && "Long Short-Term Memory (LSTM) network is a type of recurrent neural network (RNN) that is well-suited for sequence prediction problems. It can learn long-term dependencies and is effective for time series forecasting."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
