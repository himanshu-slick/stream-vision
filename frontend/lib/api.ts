import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
console.log("API_BASE_URL", process.env.NEXT_PUBLIC_API_BASE_URL);
export const startHLSStream = async (
  rtspUrl: string,
  username?: string,
  password?: string
) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/start_hls/`, {
      url: rtspUrl,
      username,
      password,
    });
    return response.data;
  } catch (error) {
    console.error("Error starting HLS stream:", error);
    throw error;
  }
};

export const getHLSStreamUrl = (streamId: string) => {
  return `${API_BASE_URL}/media/hls_media/${streamId}/stream.m3u8`;
};
