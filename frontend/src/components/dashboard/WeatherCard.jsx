const weatherDetails = [
  ["Feels like", "43°C"],
  ["Humidity", "62%"],
  ["Wind", "18 km/h"],
];
export default function WeatherCard() {
  return (
    <section className="card weather-card">
      <div className="card-heading">
        <div>
          <p className="card-kicker">KOLKATA WEATHER</p>
          <h2>Current conditions</h2>
        </div>
        <span className="sun-icon">☀</span>
      </div>
      <div className="temperature-row">
        <strong>39°</strong>
        <span>C</span>
        <p>Clear and very hot</p>
      </div>
      <div className="weather-details">
        {weatherDetails.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
