import React, { useState } from 'react';
import axios from 'axios';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { Chart as ChartJS,
  CategoryScale, 
  LinearScale, 
  BarElement, 
  PointElement, 
  LineElement, 
  ArcElement, 
  Title, 
  Tooltip, 
  Legend} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale, 
  LinearScale, 
  BarElement, 
  PointElement, 
  LineElement, 
  ArcElement, 
  Title, 
  Tooltip, 
  Legend);

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('http://localhost:8000/api/analyze-team-wins', { query });
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const renderVisualization = () => {
    if (!results) return null;
    
    const { analysis, data, league_averages } = results;
    const seasons = Object.keys(data[Object.keys(data)[0]]).map(Number).sort();
    const teams = Object.keys(data);

    // Prepare dataset based on visualization type
    const chartData = {
      labels: seasons,
      datasets: []
    };

    // Add team data
    teams.forEach(team => {
      chartData.datasets.push({
        label: team,
        data: seasons.map(season => data[team][season]),
        backgroundColor: getTeamColor(team),
        borderColor: getTeamColor(team),
        borderWidth: 2
      });
    });

    // Add league average if available
    if (league_averages && Object.keys(league_averages).length > 0) {
      chartData.datasets.push({
        label: 'League Average',
        data: seasons.map(season => league_averages[season]),
        borderColor: '#888',
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [5, 5],
        type: 'line'
      });
    }

    const options = {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: `Team Wins Analysis (${seasons.length === 1 ? seasons[0] : `${seasons[0]}–${seasons[seasons.length - 1]}`})`
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Number of Wins' }
        }
      }
    };

    switch (analysis.visualization_type) {
      case 'line':
        return <Line data={chartData} options={options} />;
      case 'pie':
        // For pie charts, we only show one season
        const lastSeason = seasons[seasons.length-1];
        return <Pie data={{
          labels: teams,
          datasets: [{
            data: teams.map(team => data[team][lastSeason]),
            backgroundColor: teams.map(getTeamColor)
          }]
        }} />;
      case 'bar':
      default:
        return <Bar data={chartData} options={options} />;
    }
  };

  // Helper function for team colors
  const getTeamColor = (teamName) => {
    const teamColors = {
      'Los Angeles Lakers': '#552583',
      'Boston Celtics': '#007A33',
      'Golden State Warriors': '#1D428A',
      'Chicago Bulls': '#CE1141',
      'Miami Heat': '#98002E',
      // Add more team colors as needed
    };
    return teamColors[teamName] || `#${Math.floor(Math.random()*16777215).toString(16)}`;
  };

  return (
    <div style={{ maxWidth: 900, margin: 'auto', padding: 20 }}>
      <h1>NBA Team Wins Analyzer</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
        <input
          type="text"
          placeholder="Enter your query, e.g. 'Compare Lakers and Celtics 2018-2023'"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: '80%', padding: 8, fontSize: 16 }}
        />
        <button type="submit" disabled={loading} style={{ padding: '8px 16px', marginLeft: 10 }}>
          {loading ? 'Loading...' : 'Analyze'}
        </button>
      </form>
      {error && <div style={{ color: 'red', marginBottom: 20 }}>{error}</div>}
      {renderVisualization()}
    </div>
  );
}

export default App;
