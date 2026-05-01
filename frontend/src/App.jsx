import { useState } from "react";

const BASE_URL = "http://localhost:8000";

export default function App() {
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  // Helper function to handle all API calls with cookies enabled
  const makeRequest = async (endpoint, method = "GET", body = null) => {
    setResponse(null);
    setError(null);
    try {
      const options = {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // REQUIRED FOR SESSION COOKIES
      };

      if (body) {
        options.body = JSON.stringify(body);
      }

      const res = await fetch(`${BASE_URL}${endpoint}`, options);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || JSON.stringify(data));
      }

      setResponse(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8 font-mono">
      <h1 className="text-3xl font-bold mb-6 text-blue-400">Poker API Dashboard</h1>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        {/* Check root to see if backend is alive */}
        <button 
          onClick={() => makeRequest("/")}
          className="bg-gray-700 hover:bg-gray-600 p-3 rounded"
        >
          Ping API (Root)
        </button>

        {/* Start a new game / Initial session creation */}
        <button 
          onClick={() => makeRequest("/game/new", "POST")}
          className="bg-green-700 hover:bg-green-600 p-3 rounded font-bold"
        >
          POST /game/new
        </button>

        {/* View current game state (also reveals the UUID) */}
        <button 
          onClick={() => makeRequest("/game", "GET")}
          className="bg-blue-700 hover:bg-blue-600 p-3 rounded"
        >
          GET /game (Check Session)
        </button>

        {/* Play Action: Keep */}
        <button 
          onClick={() => makeRequest("/action", "POST", { action: "keep" })}
          className="bg-yellow-600 hover:bg-yellow-500 p-3 rounded"
        >
          POST /action (Keep)
        </button>

        {/* Play Action: Give */}
        <button 
          onClick={() => makeRequest("/action", "POST", { action: "give" })}
          className="bg-orange-600 hover:bg-orange-500 p-3 rounded"
        >
          POST /action (Give)
        </button>

        {/* Get Results */}
        <button 
          onClick={() => makeRequest("/results", "GET")}
          className="bg-purple-700 hover:bg-purple-600 p-3 rounded"
        >
          GET /results
        </button>
      </div>

      <div className="bg-black p-4 rounded border border-gray-700 min-h-[300px] overflow-auto">
        <h2 className="text-xl text-gray-400 mb-2">Raw JSON Response:</h2>
        
        {error && (
          <div className="text-red-500 mb-4 whitespace-pre-wrap">
            <strong>Error:</strong> {error}
          </div>
        )}

        {response && (
          <pre className="text-green-400 text-sm whitespace-pre-wrap break-all">
            {JSON.stringify(response, null, 2)}
          </pre>
        )}

        {!response && !error && (
          <p className="text-gray-600 italic">Click a button to send a request...</p>
        )}
      </div>
    </div>
  );
}
