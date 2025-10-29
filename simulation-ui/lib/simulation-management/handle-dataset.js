import useGlobalState from "@/hooks/use-global-state";
import axios from "axios";

export const startDactSample = async () => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_dact_sample`
    );
  } catch (error) {
    setDataError(`Failed to get DACT sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};

export const startRandomGeneratedSample = async () => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_random_generated_sample`
    );
  } catch (error) {
    setDataError(`Failed to get Random Generated sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};

export const getDatasetInfo = async () => {
  const {setLoadingData, setDataError, setDatasetInfo } = useGlobalState.getState();

  try {
    setLoadingData(true);
    const response = await axios.get(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/get_dataset_info`
    );
    setDatasetInfo(response.data)
  } catch (error) {
    setDataError(`Failed to get dataset info: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
