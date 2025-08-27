import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import useGlobalState from "@/hooks/use-global-state";

export default function CurrentAlgorithmCard() {
  const { selectedModel, models } = useGlobalState();
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Current Algorithm</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-sm">
          <div className="font-medium mb-2">{models[selectedModel]}</div>
          <div className="text-xs text-gray-600">
            {selectedModel === "lstm" &&
              "Long Short-Term Memory (LSTM) network is a type of recurrent neural network (RNN) that is well-suited for sequence prediction problems. It can learn long-term dependencies and is effective for time series forecasting."}
            {selectedModel === "cnn" &&
              "Convolutional Neural Network (CNN) is a deep learning algorithm that can take in an input image, assign importance (learnable weights and biases) to various aspects/objects in the image, and be able to differentiate one from the other."}
            {selectedModel === "rnn" &&
              "Recurrent Neural Network (RNN) is a class of neural networks that is well-suited for sequence prediction problems. It can use its internal memory to process sequences of inputs."}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
