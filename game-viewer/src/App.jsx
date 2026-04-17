import React, { useState, useEffect, useRef } from 'react';
import { Thermometer, Gauge, Zap, Play, Pause, RotateCcw, Info } from 'lucide-react';

const ThermodynamicsEducationalGame = () => {
  const [mode, setMode] = useState('simulation');
  const [pressure, setPressure] = useState(1);
  const [volume, setVolume] = useState(2);
  const [temperature, setTemperature] = useState(300);
  const [gasParticles, setGasParticles] = useState([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [quizQuestion, setQuizQuestion] = useState(0);
  const [quizAnswer, setQuizAnswer] = useState('');
  const [quizScore, setQuizScore] = useState(0);
  const canvasRef = useRef(null);

  // Initialize gas particles
  useEffect(() => {
    const particles = [];
    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * 400,
        y: Math.random() * 300,
        vx: (Math.random() - 0.5) * 4,
        vy: (Math.random() - 0.5) * 4,
        size: Math.random() * 3 + 2
      });
    }
    setGasParticles(particles);
  }, []);

  // Animation loop for gas particles
  useEffect(() => {
    if (!isSimulating) return;
    
    const animate = () => {
      setGasParticles(prev => prev.map(particle => {
        let newX = particle.x + particle.vx;
        let newY = particle.y + particle.vy;
        let newVx = particle.vx;
        let newVy = particle.vy;

        // Bounce off walls
        if (newX <= 0 || newX >= 400) newVx *= -1;
        if (newY <= 0 || newY >= 300) newVy *= -1;

        // Adjust speed based on temperature
        const tempFactor = temperature / 300;
        const speedAdjustment = Math.min(Math.max(tempFactor, 0.5), 2);
        
        return {
          ...particle,
          x: Math.max(0, Math.min(400, newX)),
          y: Math.max(0, Math.min(300, newY)),
          vx: newVx * speedAdjustment,
          vy: newVy * speedAdjustment
        };
      }));
    };

    const interval = setInterval(animate, 50);
    return () => clearInterval(interval);
  }, [isSimulating, temperature]);

  const calculateVolume = () => {
    // Gay-Lussac: V ∝ T (constant P)
    return (temperature / 300) * 2; // Base volume at 300K
  };

  const calculatePressure = () => {
    // Ideal gas law: P ∝ T/V
    return (temperature / volume).toFixed(2);
  };

  const handleQuizSubmit = () => {
    const correctAnswers = [
      "Gay-Lussac",
      "volume",
      "tekanan"
    ];
    
    if (quizAnswer.toLowerCase() === correctAnswers[quizQuestion].toLowerCase()) {
      setQuizScore(prev => prev + 1);
    }
    
    if (quizQuestion < 2) {
      setQuizQuestion(prev => prev + 1);
      setQuizAnswer('');
    } else {
      alert(`Skor Anda: ${quizScore + 1}/3`);
      setQuizQuestion(0);
      setQuizScore(0);
      setQuizAnswer('');
    }
  };

  const resetSimulation = () => {
    setPressure(1);
    setVolume(2);
    setTemperature(300);
  };

  const renderSimulation = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <h3 className="text-xl font-bold text-blue-600">Simulator Gas Ideal</h3>
        
        <div className="bg-white rounded-lg shadow-md p-4">
          <canvas
            ref={canvasRef}
            width={400}
            height={300}
            className="border border-gray-300 rounded bg-gradient-to-b from-sky-100 to-blue-50"
            style={{ background: `linear-gradient(to bottom, #e0f2fe, #f0f9ff)` }}
          >
            {gasParticles.map((particle, index) => (
              <div
                key={index}
                className="absolute rounded-full bg-blue-400 opacity-70"
                style={{
                  left: `${particle.x}px`,
                  top: `${particle.y}px`,
                  width: `${particle.size}px`,
                  height: `${particle.size}px`,
                  backgroundColor: `hsl(${200 + (temperature - 273) * 0.5}, 70%, 60%)`
                }}
              />
            ))}
          </canvas>
          
          <div className="flex justify-center mt-2 space-x-4">
            <button
              onClick={() => setIsSimulating(!isSimulating)}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              {isSimulating ? <Pause size={16} /> : <Play size={16} />}
              {isSimulating ? 'Jeda' : 'Mulai'}
            </button>
            <button
              onClick={resetSimulation}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4 rounded-lg">
            <Gauge size={24} className="mb-2" />
            <label className="block text-sm mb-1">Tekanan (atm)</label>
            <input
              type="range"
              min="0.1"
              max="3"
              step="0.1"
              value={pressure}
              onChange={(e) => setPressure(parseFloat(e.target.value))}
              className="w-full"
            />
            <span className="font-bold">{pressure.toFixed(1)} atm</span>
          </div>
          
          <div className="bg-gradient-to-r from-red-500 to-red-600 text-white p-4 rounded-lg">
            <Thermometer size={24} className="mb-2" />
            <label className="block text-sm mb-1">Suhu (K)</label>
            <input
              type="range"
              min="200"
              max="500"
              step="10"
              value={temperature}
              onChange={(e) => setTemperature(parseInt(e.target.value))}
              className="w-full"
            />
            <span className="font-bold">{temperature} K</span>
          </div>
          
          <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white p-4 rounded-lg">
            <Zap size={24} className="mb-2" />
            <label className="block text-sm mb-1">Volume (L)</label>
            <input
              type="range"
              min="0.5"
              max="5"
              step="0.1"
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
              className="w-full"
            />
            <span className="font-bold">{volume.toFixed(1)} L</span>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h4 className="text-lg font-semibold mb-4">Hukum-Hukum Termodinamika</h4>
          <div className="space-y-3">
            <div className="border-l-4 border-blue-500 pl-4">
              <h5 className="font-medium">Hukum Gay-Lussac</h5>
              <p className="text-sm text-gray-600">V/T = konstan (P konstan)</p>
            </div>
            <div className="border-l-4 border-green-500 pl-4">
              <h5 className="font-medium">Hukum Charles</h5>
              <p className="text-sm text-gray-600">V/T = konstan (P konstan)</p>
            </div>
            <div className="border-l-4 border-purple-500 pl-4">
              <h5 className="font-medium">Hukum Boyle</h5>
              <p className="text-sm text-gray-600">PV = konstan (T konstan)</p>
            </div>
            <div className="border-l-4 border-orange-500 pl-4">
              <h5 className="font-medium">Hukum Ideal Gas</h5>
              <p className="text-sm text-gray-600">PV = nRT</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-r from-yellow-400 to-orange-500 text-white p-6 rounded-lg">
          <h4 className="text-lg font-semibold mb-2">Perhitungan Otomatis</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p>Volume Terhitung:</p>
              <p className="font-bold text-xl">{calculateVolume().toFixed(2)} L</p>
            </div>
            <div>
              <p>Tekanan Terhitung:</p>
              <p className="font-bold text-xl">{calculatePressure()} atm</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderQuiz = () => (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-8">
      <h3 className="text-2xl font-bold text-center mb-6 text-blue-600">Kuis Termodinamika</h3>
      
      {quizQuestion < 3 && (
        <div className="space-y-6">
          <div className="bg-gray-50 p-6 rounded-lg">
            <h4 className="text-lg font-semibold mb-4">
              Soal {quizQuestion + 1}: {[
                "Hukum apa yang menyatakan bahwa volume gas sebanding dengan suhu mutlaknya pada tekanan konstan?",
                "Dalam hukum Gay-Lussac, jika suhu meningkat maka apa yang terjadi pada volume?",
                "Apa yang dijaga konstan dalam eksperimen hukum Gay-Lussac?"
              ][quizQuestion]}
            </h4>
            
            <input
              type="text"
              value={quizAnswer}
              onChange={(e) => setQuizAnswer(e.target.value)}
              placeholder="Masukkan jawaban..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            
            <button
              onClick={handleQuizSubmit}
              disabled={!quizAnswer.trim()}
              className="mt-4 w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
            >
              {quizQuestion === 2 ? 'Selesai' : 'Lanjut'}
            </button>
          </div>
        </div>
      )}
      
      {quizQuestion >= 3 && (
        <div className="text-center">
          <h4 className="text-xl font-semibold mb-4">Kuis Selesai!</h4>
          <p className="text-lg">Skor Anda: {quizScore}/3</p>
        </div>
      )}
    </div>
  );

  const renderLab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-bold mb-4">Laboratorium Virtual</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4>Eksperimen: Volume vs Tekanan</h4>
            <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center relative overflow-hidden">
              <svg width="100%" height="100%" viewBox="0 0 400 200">
                <line x1="50" y1="180" x2="350" y2="180" stroke="#333" strokeWidth="2"/>
                <line x1="50" y1="180" x2="50" y2="20" stroke="#333" strokeWidth="2"/>
                {/* Sample PV curve */}
                <path d="M50,180 Q150,100 250,60 Q350,40 350,40" fill="none" stroke="#3b82f6" strokeWidth="3"/>
                <circle cx="100" cy="140" r="4" fill="#ef4444"/>
                <circle cx="150" cy="100" r="4" fill="#ef4444"/>
                <circle cx="200" cy="70" r="4" fill="#ef4444"/>
                <circle cx="250" cy="50" r="4" fill="#ef4444"/>
                <circle cx="300" cy="40" r="4" fill="#ef4444"/>
              </svg>
            </div>
          </div>
          <div className="space-y-4">
            <h4>Eksperimen: Suhu vs Volume</h4>
            <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center relative overflow-hidden">
              <svg width="100%" height="100%" viewBox="0 0 400 200">
                <line x1="50" y1="180" x2="350" y2="180" stroke="#333" strokeWidth="2"/>
                <line x1="50" y1="180" x2="50" y2="20" stroke="#333" strokeWidth="2"/>
                {/* Sample VT curve */}
                <path d="M50,180 L100,150 L150,120 L200,90 L250,60 L300,30" fill="none" stroke="#10b981" strokeWidth="3"/>
                <circle cx="100" cy="150" r="4" fill="#ef4444"/>
                <circle cx="150" cy="120" r="4" fill="#ef4444"/>
                <circle cx="200" cy="90" r="4" fill="#ef4444"/>
                <circle cx="250" cy="60" r="4" fill="#ef4444"/>
                <circle cx="300" cy="30" r="4" fill="#ef4444"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-6 rounded-lg">
        <h4 className="text-lg font-semibold mb-2">Simulasi Proses Termal</h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-white bg-opacity-20 p-4 rounded">
            <div className="text-2xl">🔥</div>
            <p>Panas Masuk</p>
            <p className="text-sm">{temperature > 350 ? 'TINGGI' : 'RENDAH'}</p>
          </div>
          <div className="bg-white bg-opacity-20 p-4 rounded">
            <div className="text-2xl">🌡️</div>
            <p>Suhu</p>
            <p className="text-sm">{temperature}K</p>
          </div>
          <div className="bg-white bg-opacity-20 p-4 rounded">
            <div className="text-2xl">📊</div>
            <p>Proses</p>
            <p className="text-sm">{temperature > 350 ? 'ISOBAR' : 'ISOTERM'}</p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">Game Edukasi Termodinamika</h1>
            <div className="flex space-x-2">
              <button
                onClick={() => setMode('simulation')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  mode === 'simulation' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Simulasi
              </button>
              <button
                onClick={() => setMode('quiz')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  mode === 'quiz' 
                    ? 'bg-green-500 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Kuis
              </button>
              <button
                onClick={() => setMode('lab')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  mode === 'lab' 
                    ? 'bg-purple-500 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Laboratorium
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {mode === 'simulation' && renderSimulation()}
        {mode === 'quiz' && renderQuiz()}
        {mode === 'lab' && renderLab()}
      </main>

      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-600">
            <p>Game Edukasi Termodinamika - Belajar Fisika dengan Cara Interaktif</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default ThermodynamicsEducationalGame;