import { useState, useEffect } from "react";
import "./App.css";

const BASE_URL = "http://localhost:8000";

const fallbackMessageForStatus = (status) => {
  switch (status) {
    case 400: return "Bad request. Please check your input.";
    case 401: return "Unauthorized. Please sign in.";
    case 403: return "Forbidden.";
    case 404: return "Not found.";
    case 422: return "Invalid request data.";
    case 429: return "Too many requests. Try again later.";
    case 500: return "Server error. Please try again later.";
    default:  return "An unexpected server error occurred.";
  }
};

// --- Helper Functions & Components ---

const parseCard = (cardStr) => {
  if (!cardStr) return null;
  const rankStr = cardStr[0];
  const suitStr = cardStr[1].toLowerCase();
  
  const rank = rankStr === 'T' ? '10' : rankStr;
  const suits = { s: '♠', h: '♥', d: '♦', c: '♣' };
  const colors = { s: 'text-black', c: 'text-black', h: 'text-red-600', d: 'text-red-600' };
  
  return { rank, suit: suits[suitStr], color: colors[suitStr] };
};

const PlayingCard = ({ cardStr }) => {
  // Empty Slot (Boundary Placeholder)
  if (!cardStr) {
    return (
      <div className="w-10 h-16 sm:w-16 sm:h-24 border-2 border-dashed border-gray-600 bg-gray-800/50 rounded sm:rounded-lg flex-shrink-0 transition-all"></div>
    );
  }
  
  const { rank, suit } = parseCard(cardStr);
  const isRed = suit === '♥' || suit === '♦';
  
  // Face Up Card (Centered Design)
  return (
    <div className="w-10 h-16 sm:w-16 sm:h-24 bg-white rounded sm:rounded-lg border border-gray-300 shadow-md flex-shrink-0 flex flex-col items-center justify-center transition-all">
      <span className={`text-lg sm:text-2xl font-bold leading-none ${isRed ? 'text-red-500' : 'text-gray-900'}`}>
        {rank}
      </span>
      <span className={`text-xl sm:text-3xl leading-none ${isRed ? 'text-red-500' : 'text-gray-900'}`}>
        {suit}
      </span>
    </div>
  );
};

// --- Main App Component ---

export default function App() {
  const [gameState, setGameState] = useState(null);
  const [result, setResult] = useState(null);
  const [hint, setHint] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [showRules, setShowRules] = useState(false); // Add this new state

  const fetchApi = async (endpoint, method = "GET", body = null) => {
    setLoading(true);
    // Don't clear UI-critical state (like result) here unless appropriate
    // setError(null);  // <-- avoid clearing/setting a global blocking error for transient 429s
    try {
      const options = {
        method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      };
      if (body) options.body = JSON.stringify(body);

      const res = await fetch(`${BASE_URL}${endpoint}`, options);

      let data = null;
      try {
        data = await res.json();
      } catch {
        const txt = await res.text().catch(() => null);
        data = txt ? { detail: txt } : null;
      }

      if (!res.ok) {
        // Special-case: non-fatal 429 on /results should not block starting a new game.
        if (res.status === 429 && endpoint === "/results") {
          // Clear any previous error so the banner doesn't remain, and return null.
          setError(null);
          console.warn("Results endpoint rate-limited. Try again shortly.");
          return null;
        }

        // Otherwise prefer backend 'detail' or a fallback message
        const errorMessage = (data && data.detail) || fallbackMessageForStatus(res.status);
        throw new Error(errorMessage);
      }

      // Success: clear any previous global error so the UI recovers visibly
      setError(null);
      return data;
    } catch (err) {
      // For non-results 429 or other failures, set error normally.
      setError(err.message || "An unexpected error occurred.");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const loadGame = async () => {
    const data = await fetchApi("/game", "GET");
    if (data) {
      setGameState(data);
      // NEW: If the game is loaded but already over (no current card), 
      // instantly fetch results so the "Game Over" screen appears and unlocks "New Game".
      if (!data.current_card) {
        const resData = await fetchApi("/results", "GET");
        if (resData) setResult(resData);
      }
    }
  };

  const startNewGame = async () => {
    setResult(null);
    setHint(null);
    setIsThinking(false);   // ensure AI state cleared
    setError(null);         // clear any stale error
    const data = await fetchApi("/game/new", "POST");
    if (data) setGameState(data);
  };

  const playAction = async (action) => {
    if (loading || isThinking) return; // Prevent overlapping requests
    setHint(null);
    const data = await fetchApi("/action", "POST", { action });
    if (data) {
      setGameState(data);
      if (!data.current_card) {
        const resData = await fetchApi("/results", "GET");
        if (resData) setResult(resData);
      }
    }
  };

  const getHint = async () => {
    setIsThinking(true);
    const data = await fetchApi("/hint", "GET");
    if (data) setHint(data);
    setIsThinking(false);
  };

  useEffect(() => {
    loadGame();
  }, []);

  let isForcedKeep = false;
  let cardsRemaining = 0; // NEW: hoist this so we can render it
  if (gameState && gameState.current_card) {
    const cardsNeeded = 5 - gameState.player_hand.length;
    cardsRemaining = 52 - (gameState.player_hand.length + gameState.dealer_hand.length + 1);
    isForcedKeep = cardsRemaining <= cardsNeeded;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 md:p-8 font-mono flex flex-col items-center overflow-x-hidden">

      {/* --- RULES MODAL --- */}
      {showRules && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in p-4">
          <div className="bg-gray-800 border border-gray-600 rounded-2xl shadow-2xl max-w-2xl w-full p-5 md:p-8 relative max-h-[90vh] overflow-y-auto">
            <button 
              onClick={() => setShowRules(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-full w-8 h-8 flex items-center justify-center font-bold text-lg transition-colors border-none"
            >
              ×
            </button>
            
            <h2 className="text-2xl md:text-3xl font-extrabold text-blue-400 mb-4 md:mb-6 border-b border-gray-700 pb-4">How to Play</h2>
            
            <div className="space-y-4 text-base md:text-lg text-gray-300 leading-relaxed font-sans">
              <p><strong className="text-white">Objective:</strong> Build a stronger 5-card poker hand than the dealer.</p>
              <p><strong className="text-white">Drafting:</strong> Cards are dealt face-up one at a time. For each card, you must choose to <span className="text-yellow-400 font-bold">KEEP</span> it for yourself or <span className="text-orange-400 font-bold">GIVE</span> it to the dealer.</p>
              <p><strong className="text-white">Ending the Game:</strong> The round immediately ends when you have exactly <strong>5 cards</strong> in your hand.</p>
              <p><strong className="text-white">Dealer Rule:</strong> The dealer uses their best 5 cards from their accumulated pool. If the dealer has fewer than 8 cards when the game ends, they will draw from the deck until they hit 8.</p>
              <p><strong className="text-white">Scoring:</strong> Standard poker rankings apply. Ties go to the dealer!</p>
            </div>
            
            <div className="mt-6 md:mt-8 text-center pt-6 border-t border-gray-700">
              <button 
                onClick={() => setShowRules(false)}
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-10 rounded-lg shadow-lg transition-transform hover:-translate-y-1 border-none"
              >
                Let's Play!
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header & Stats */}
      <div className="w-full max-w-4xl flex flex-col md:flex-row justify-between items-center mb-6 md:mb-8 pb-4 border-b border-gray-700 gap-4">
        <h1 className="text-2xl md:text-3xl font-bold text-blue-400">Holdout</h1>
        <div className="flex flex-wrap justify-center gap-3 md:gap-4 items-center">

          <button 
            onClick={() => setShowRules(true)} 
            className="text-gray-400 hover:text-white uppercase tracking-wider text-sm font-semibold border-none bg-transparent hover:underline cursor-pointer focus:outline-none"
          >
            Rules
          </button>
          {gameState && (
            <div className="text-sm text-gray-400">
              Wins: <span className="text-green-400">{gameState.wins}</span> | 
              Losses: <span className="text-red-400">{gameState.losses}</span>
            </div>
          )}
          <button 
            onClick={startNewGame} 
            // Disable only when a game is actively in progress OR when loading/thinking
            disabled={loading || isThinking || (gameState && gameState.current_card && !result)}
            title={gameState && !result ? "Finish your current game first!" : ""}
            className="bg-green-700 hover:bg-green-600 px-4 py-2 rounded font-bold text-sm md:text-base border-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            New Game
          </button>
        </div>
      </div>

      {loading && <div className="text-yellow-400 text-lg md:text-xl font-bold animate-pulse mb-4 text-center">Processing...</div>}
      
      {error && (
        <div className="bg-red-900 border border-red-500 rounded p-4 mb-4 text-white w-full max-w-4xl text-sm md:text-base text-center">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Game Board */}
      {gameState ? (
        <div className="w-full max-w-4xl grid gap-4 md:gap-8 rounded-xl bg-gray-800 p-4 md:p-8 border border-gray-700 shadow-2xl">
          {/* Dealer Area */}
          <div className="bg-gray-700/30 p-3 sm:p-4 rounded-lg border border-gray-700 w-full overflow-hidden">
            <h2 className="text-base sm:text-lg text-gray-400 mb-3 sm:mb-4 flex justify-between uppercase tracking-wider font-semibold">
              <span>Dealer's Hand</span>
              <span>{gameState.dealer_hand.length} / 8</span>
            </h2>
            {/* NEW: flex-nowrap on mobile, overflow-x-auto, adjusted gaps */}
            <div className="flex flex-nowrap sm:flex-wrap gap-1.5 sm:gap-3 min-h-[4.5rem] sm:min-h-[7rem] pb-2 overflow-x-auto scrollbar-hide">
              {[...Array(Math.max(8, gameState.dealer_hand.length))].map((_, i) => (
                <PlayingCard 
                  key={`dealer-${i}`} 
                  cardStr={gameState.dealer_hand[i]} 
                />
              ))}
            </div>
          </div>

          {/* Table / Action Area */}
          <div className="flex flex-col items-center py-6 min-h-[16rem] justify-center text-center relative border border-gray-700 rounded-lg bg-gray-900/50 overflow-hidden">
            {result && (
              <div className="absolute inset-0 bg-gray-900/90 flex flex-col items-center justify-center z-10 rounded-lg backdrop-blur-sm animate-fade-in shadow-xl">
                <h2 className="text-5xl font-extrabold text-yellow-400 mb-4 drop-shadow-md">Game Over!</h2>
                <p className="text-2xl text-white font-bold">Winner: <span className="text-blue-400">{result.winner.toUpperCase()}</span></p>
                <div className="mt-4 text-gray-300 mb-6">{result.message}</div>
                {/* NEW: Play Again Button inside the modal */}
                <button 
                  onClick={startNewGame}
                  className="bg-green-600 hover:bg-green-500 text-white font-bold py-3 px-8 rounded-lg shadow-lg transition-transform hover:-translate-y-1 border-none"
                >
                  Play Again
                </button>
              </div>
            )}

            <div className="flex justify-between w-full max-w-sm px-4 mb-4">
              <h2 className="text-sm uppercase tracking-widest text-blue-300 font-bold">Current Card</h2>
              {/* NEW: Display cards remaining in deck */}
              <h2 className="text-sm uppercase tracking-widest text-gray-400 font-bold">Deck: {cardsRemaining}</h2>
            </div>
            
            {/* NEW: Increased mobile scale so it still looks like the main focal point */}
            <div className="mb-6 mt-4 sm:mt-0 scale-[1.3] sm:scale-125 transition-transform">
              <PlayingCard cardStr={!result ? gameState.current_card : null} />
            </div>
            
            {!result && gameState.current_card && (
              <div className="flex flex-col items-center gap-4 relative z-0 w-full px-2">
                <div className="flex flex-wrap justify-center gap-3 w-full">
                  <button 
                    onClick={() => playAction("keep")} 
                    disabled={loading || isThinking} 
                    className={`bg-yellow-600 hover:bg-yellow-500 flex-1 sm:flex-none px-4 sm:px-8 py-3 rounded-lg font-bold text-base sm:text-lg shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed border-none ${hint?.action === 'keep' ? 'ring-4 ring-yellow-400 ring-offset-2 ring-offset-gray-900 scale-105' : 'hover:-translate-y-1'}`}
                  >
                    Keep
                  </button>
                  <button 
                    onClick={() => playAction("give")} 
                    disabled={loading || isThinking || isForcedKeep}
                    className={`bg-orange-600 hover:bg-orange-500 flex-1 sm:flex-none px-4 sm:px-8 py-3 rounded-lg font-bold text-base sm:text-lg shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed border-none ${hint?.action === 'give' ? 'ring-4 ring-orange-400 ring-offset-2 ring-offset-gray-900 scale-105' : 'hover:-translate-y-1'}`}
                  >
                    Give
                  </button>
                  <button 
                    onClick={getHint} 
                    disabled={isThinking || hint !== null || loading} 
                    className="bg-indigo-600 hover:bg-indigo-500 w-full sm:w-auto px-6 py-3 rounded-lg font-bold shadow-lg transition-transform hover:-translate-y-1 disabled:opacity-50 disabled:cursor-not-allowed border-none"
                  >
                    Hint
                  </button>
                </div>

                {/* NEW: Clear text warning for forced keep */}
                {isForcedKeep && (
                  <div className="text-red-400 text-sm font-bold animate-pulse mt-2">
                    Must keep! Not enough cards left to finish your hand.
                  </div>
                )}
              </div>
            )}

            {/* NEW: Wait indicator for fetching results */}
            {!result && !gameState.current_card && loading && (
              <div className="mt-4 p-4 flex flex-col items-center justify-center animate-pulse z-10 relative">
                <svg className="animate-spin h-8 w-8 text-yellow-400 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <strong className="text-yellow-400 text-xl tracking-wide">Calculating Match Results...</strong>
              </div>
            )}

            {!result && isThinking && (
              <div className="mt-4 p-3 bg-blue-900/80 border border-blue-400 rounded text-center shadow-lg min-w-[250px] flex items-center justify-center gap-3 animate-pulse">
                <svg className="animate-spin h-5 w-5 text-blue-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <strong className="text-blue-300 tracking-wide">AI is computing...</strong>
              </div>
            )}

            {!result && !isThinking && hint && (
              <div className="mt-4 p-3 bg-indigo-900/80 border border-indigo-400 rounded text-center shadow-lg">
                AI Suggests: <strong className="uppercase text-yellow-300">{hint.action}</strong>
                <div className="text-sm mt-1 text-indigo-200">
                  Keep Utility: {hint.keep_delta.toFixed(2)} | Give Utility: {hint.give_delta.toFixed(2)}
                </div>
              </div>
            )}
          </div>

          {/* Player Area */}
          <div className="bg-gray-700/30 p-3 sm:p-4 rounded-lg border border-gray-700 w-full overflow-hidden">
            <h2 className="text-base sm:text-lg text-gray-400 mb-3 sm:mb-4 flex justify-between uppercase tracking-wider font-semibold">
              <span>Your Hand</span>
              <span>{gameState.player_hand.length} / 5</span>
            </h2>
            {/* NEW: Adjusted gap and min-height for player hand */}
            <div className="flex gap-1.5 sm:gap-3 min-h-[4.5rem] sm:min-h-[7rem] overflow-x-auto pb-2 scrollbar-hide">
              {[...Array(5)].map((_, i) => (
                <PlayingCard key={`player-${i}`} cardStr={gameState.player_hand[i]} />
              ))}
            </div>
          </div>

        </div>
      ) : (
        !loading && <div className="text-xl text-gray-500 mt-10">Click "New Game" to start.</div>
      )}
    </div>
  );
}
