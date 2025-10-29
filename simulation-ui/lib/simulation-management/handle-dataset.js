import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const setDataset = async (datasetName, sampleSize = null) => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    const payload = { dataset_name: datasetName };
    if (sampleSize !== null) {
      payload.sample_size = sampleSize;
    }
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/set_dataset`,
      payload
    );
  } catch (error) {
    setDataError(`Failed to set dataset: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
}

export const getDatasetInfo = async () => {
  const {setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    const response = await axios.get(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_dataset_info`
    );
    return response.data?.data;
  } catch (error) {
    setDataError(`Failed to get dataset info: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
