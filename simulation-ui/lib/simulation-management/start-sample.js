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

export const startVehiclesSample = async () => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_vehicles_sample`
    );
  } catch (error) {
    setDataError(`Failed to get Vehicle sample: ${error.message}`);
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

export const startTaxiDSample = async () => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_taxid_sample`
    );
  } catch (error) {
    setDataError(`Failed to start TaxiD sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};

export const startTaxiDReplaySample = async () => {
  const { setLoadingData, setDataError } = useGlobalState.getState();

  try {
    setLoadingData(true);
    await axios.post(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/central/start_taxid_replay_sample`
    );
  } catch (error) {
    setDataError(`Failed to start TaxiD replay sample: ${error.message}`);
  } finally {
    setLoadingData(false);
  }
};
