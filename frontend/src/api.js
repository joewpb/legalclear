import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL;
if (!baseURL) {
  console.warn("VITE_API_URL not set. API calls will fail.");
}

const api = axios.create({
  baseURL,
  headers: {
    "X-API-Key": import.meta.env.VITE_API_KEY,
  },
});

export default api;
